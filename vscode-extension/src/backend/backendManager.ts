/**
 * Backend Manager
 * 
 * Manages the Python backend lifecycle and WebSocket connection.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { ChildProcess, spawn } from 'child_process';
import { EventBus, Events } from '../events/eventBus';
import { WebSocketClient, Message } from './websocketClient';

export interface BackendConfig {
    host: string;
    port: number;
    pythonPath?: string;
}

export class BackendManager implements vscode.Disposable {
    private context: vscode.ExtensionContext;
    private eventBus: EventBus;
    private process: ChildProcess | null = null;
    private wsClient: WebSocketClient | null = null;
    private outputChannel: vscode.OutputChannel;
    private isConnected: boolean = false;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 5;

    constructor(context: vscode.ExtensionContext, eventBus: EventBus) {
        this.context = context;
        this.eventBus = eventBus;
        this.outputChannel = vscode.window.createOutputChannel('OMNI Backend');
    }

    /**
     * Get backend configuration from VS Code settings.
     */
    getConfig(): BackendConfig {
        const config = vscode.workspace.getConfiguration('omni');
        return {
            host: config.get<string>('backend.host', 'localhost'),
            port: config.get<number>('backend.port', 8765),
            pythonPath: config.get<string>('backend.pythonPath'),
        };
    }

    /**
     * Start the backend server.
     */
    async start(): Promise<void> {
        const config = this.getConfig();
        
        this.eventBus.emit(Events.BACKEND_STARTING);
        this.outputChannel.appendLine('Starting OMNI backend...');

        // Try to connect to existing backend first
        try {
            await this.connect(config);
            return;
        } catch {
            this.outputChannel.appendLine('No existing backend found, starting new instance...');
        }

        // Start new backend process
        await this.startProcess(config);
        
        // Wait for backend to be ready
        await this.waitForBackend(config);
        
        // Connect WebSocket
        await this.connect(config);
    }

    /**
     * Start the backend Python process.
     */
    private async startProcess(config: BackendConfig): Promise<void> {
        const backendPath = this.getBackendPath();
        const pythonPath = this.getPythonPath(config, backendPath);

        this.outputChannel.appendLine(`Backend path: ${backendPath}`);
        this.outputChannel.appendLine(`Python: ${pythonPath}`);

        return new Promise((resolve, reject) => {
            this.process = spawn(pythonPath, ['-m', 'backend.server.main'], {
                cwd: backendPath,
                env: {
                    ...process.env,
                    OMNI_SERVER__HOST: config.host,
                    OMNI_SERVER__PORT: config.port.toString(),
                },
            });

            this.process.stdout?.on('data', (data) => {
                this.outputChannel.append(data.toString());
            });

            this.process.stderr?.on('data', (data) => {
                this.outputChannel.append(data.toString());
            });

            this.process.on('error', (error) => {
                this.outputChannel.appendLine(`Process error: ${error.message}`);
                this.eventBus.emit(Events.BACKEND_ERROR, error);
                reject(error);
            });

            this.process.on('exit', (code) => {
                this.outputChannel.appendLine(`Backend process exited with code ${code}`);
                this.isConnected = false;
                this.eventBus.emit(Events.BACKEND_DISCONNECTED);
            });

            // Give the process time to start
            setTimeout(resolve, 2000);
        });
    }

    /**
     * Get the Python executable path, with auto-detection for venv.
     */
    private getPythonPath(config: BackendConfig, backendPath: string): string {
        // If explicitly configured, use that
        if (config.pythonPath) {
            return config.pythonPath;
        }

        // Try to find venv in the backend path
        const isWindows = process.platform === 'win32';
        const venvPaths = [
            // Check .venv folder (common convention)
            path.join(backendPath, '.venv', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python'),
            // Check venv folder
            path.join(backendPath, 'venv', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python'),
            // Check env folder
            path.join(backendPath, 'env', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python'),
        ];

        for (const venvPath of venvPaths) {
            if (fs.existsSync(venvPath)) {
                this.outputChannel.appendLine(`Found venv Python at: ${venvPath}`);
                return venvPath;
            }
        }

        // Fallback to system Python
        this.outputChannel.appendLine('No venv found, using system Python');
        return 'python';
    }

    /**
     * Wait for the backend to be ready.
     */
    private async waitForBackend(config: BackendConfig): Promise<void> {
        const maxAttempts = 30;
        const delayMs = 500;
        // Health endpoint runs on port+1 (see backend.server.main)
        const healthPort = config.port + 1;

        for (let i = 0; i < maxAttempts; i++) {
            try {
                const response = await fetch(
                    `http://${config.host}:${healthPort}/health`
                );
                if (response.ok) {
                    this.outputChannel.appendLine('Backend is ready');
                    return;
                }
            } catch {
                // Backend not ready yet
            }
            await new Promise(r => setTimeout(r, delayMs));
        }

        throw new Error('Backend failed to start in time');
    }

    /**
     * Connect to the backend via WebSocket.
     */
    private async connect(config: BackendConfig): Promise<void> {
        const wsUrl = `ws://${config.host}:${config.port}/ws`;
        
        this.wsClient = new WebSocketClient(wsUrl, {
            onOpen: () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.outputChannel.appendLine('WebSocket connected');
                this.eventBus.emit(Events.BACKEND_CONNECTED);
            },
            onClose: () => {
                this.isConnected = false;
                this.outputChannel.appendLine('WebSocket disconnected');
                this.eventBus.emit(Events.BACKEND_DISCONNECTED);
                this.handleReconnect(config);
            },
            onError: (error) => {
                this.outputChannel.appendLine(`WebSocket error: ${error}`);
                this.eventBus.emit(Events.BACKEND_ERROR, error);
            },
            onMessage: (message) => {
                this.handleMessage(message);
            },
        });

        await this.wsClient.connect();
    }

    /**
     * Handle reconnection attempts.
     */
    private async handleReconnect(config: BackendConfig): Promise<void> {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.outputChannel.appendLine('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        
        this.outputChannel.appendLine(
            `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`
        );

        await new Promise(r => setTimeout(r, delay));
        
        try {
            await this.connect(config);
        } catch {
            // Will retry via onClose handler
        }
    }

    /**
     * Handle incoming WebSocket messages.
     */
    private handleMessage(message: Message): void {
        switch (message.type) {
            case 'chat_response':
                this.eventBus.emit(Events.CHAT_MESSAGE_RECEIVED, message.data);
                break;
            case 'stream_start':
                this.eventBus.emit(Events.CHAT_STREAM_START, message.data);
                break;
            case 'stream_chunk':
                this.eventBus.emit(Events.CHAT_STREAM_CHUNK, message.data);
                break;
            case 'stream_end':
                this.eventBus.emit(Events.CHAT_STREAM_END, message.data);
                break;
            case 'agent_list':
                this.eventBus.emit(Events.AGENT_LIST_UPDATED, message.data);
                break;
            case 'agent_status':
                this.eventBus.emit(Events.AGENT_STATUS_CHANGED, message.data);
                break;
            case 'analysis_result':
                this.eventBus.emit('analysis:result', message.data);
                break;
            case 'security_findings':
                this.eventBus.emit('security:findings', message.data);
                break;
            case 'error':
                this.eventBus.emit(Events.CHAT_ERROR, message.data);
                break;
            default:
                this.outputChannel.appendLine(`Unknown message type: ${message.type}`);
        }
    }

    /**
     * Send a message to the backend.
     */
    async send(type: string, data: any): Promise<void> {
        if (!this.wsClient || !this.isConnected) {
            throw new Error('Not connected to backend');
        }
        await this.wsClient.send({ type, data });
    }

    /**
     * Send a raw message object to the backend.
     * Used by FileWatcher and other components.
     */
    async sendMessage(message: { type: string; data: any }): Promise<void> {
        await this.send(message.type, message.data);
    }

    /**
     * Send a chat message.
     */
    async sendChatMessage(content: string, agentId?: string): Promise<void> {
        await this.send('chat_message', {
            content,
            agent_id: agentId,
        });
        this.eventBus.emit(Events.CHAT_MESSAGE_SENT, { content, agentId });
    }

    /**
     * Get available agents.
     */
    async getAgents(): Promise<void> {
        await this.send('get_agents', {});
    }

    /**
     * Select an agent.
     */
    async selectAgent(agentId: string): Promise<void> {
        await this.send('select_agent', { agent_id: agentId });
        this.eventBus.emit(Events.AGENT_SELECTED, { agentId });
    }

    /**
     * Enable an agent on the backend.
     */
    async enableAgent(agentId: string): Promise<void> {
        await this.send('enable_agent', { agent_id: agentId });
    }

    /**
     * Disable an agent on the backend.
     */
    async disableAgent(agentId: string): Promise<void> {
        await this.send('disable_agent', { agent_id: agentId });
    }

    /**
     * Check if connected to backend.
     */
    get connected(): boolean {
        return this.isConnected;
    }

    /**
     * Stop the backend.
     */
    async stop(): Promise<void> {
        this.outputChannel.appendLine('Stopping OMNI backend...');

        if (this.wsClient) {
            this.wsClient.disconnect();
            this.wsClient = null;
        }

        if (this.process) {
            this.process.kill();
            this.process = null;
        }

        this.isConnected = false;
        this.eventBus.emit(Events.BACKEND_DISCONNECTED);
    }

    /**
     * Restart the backend.
     */
    async restart(): Promise<void> {
        await this.stop();
        await new Promise(r => setTimeout(r, 1000));
        await this.start();
    }

    /**
     * Get the backend directory path.
     * Returns the root OMNI folder (parent of vscode-extension and backend).
     */
    private getBackendPath(): string {
        // In development, backend is sibling to vscode-extension
        // We need to return the OMNI root folder, not the backend folder,
        // because Python needs to run from root to find 'backend' module
        const extensionPath = this.context.extensionPath;
        return path.join(extensionPath, '..');
    }

    /**
     * Show the output channel.
     */
    showOutput(): void {
        this.outputChannel.show();
    }

    dispose(): void {
        this.stop();
        this.outputChannel.dispose();
    }
}
