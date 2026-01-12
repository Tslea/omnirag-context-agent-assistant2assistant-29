/**
 * Backend Manager
 *
 * Manages the Python backend lifecycle and WebSocket connection.
 */
import * as vscode from 'vscode';
import { EventBus } from '../events/eventBus';
export interface BackendConfig {
    host: string;
    port: number;
    pythonPath?: string;
}
export declare class BackendManager implements vscode.Disposable {
    private context;
    private eventBus;
    private process;
    private wsClient;
    private outputChannel;
    private isConnected;
    private reconnectAttempts;
    private maxReconnectAttempts;
    constructor(context: vscode.ExtensionContext, eventBus: EventBus);
    /**
     * Get backend configuration from VS Code settings.
     */
    getConfig(): BackendConfig;
    /**
     * Start the backend server.
     */
    start(): Promise<void>;
    /**
     * Start the backend Python process.
     */
    private startProcess;
    /**
     * Get the Python executable path, with auto-detection for venv.
     */
    private getPythonPath;
    /**
     * Wait for the backend to be ready.
     */
    private waitForBackend;
    /**
     * Connect to the backend via WebSocket.
     */
    private connect;
    /**
     * Handle reconnection attempts.
     */
    private handleReconnect;
    /**
     * Handle incoming WebSocket messages.
     */
    private handleMessage;
    /**
     * Send a message to the backend.
     */
    send(type: string, data: any): Promise<void>;
    /**
     * Send a raw message object to the backend.
     * Used by FileWatcher and other components.
     */
    sendMessage(message: {
        type: string;
        data: any;
    }): Promise<void>;
    /**
     * Send a chat message.
     */
    sendChatMessage(content: string, agentId?: string): Promise<void>;
    /**
     * Get available agents.
     */
    getAgents(): Promise<void>;
    /**
     * Select an agent.
     */
    selectAgent(agentId: string): Promise<void>;
    /**
     * Enable an agent on the backend.
     */
    enableAgent(agentId: string): Promise<void>;
    /**
     * Disable an agent on the backend.
     */
    disableAgent(agentId: string): Promise<void>;
    /**
     * Check if connected to backend.
     */
    get connected(): boolean;
    /**
     * Stop the backend.
     */
    stop(): Promise<void>;
    /**
     * Restart the backend.
     */
    restart(): Promise<void>;
    /**
     * Get the backend directory path.
     * Returns the root OMNI folder (parent of vscode-extension and backend).
     */
    private getBackendPath;
    /**
     * Show the output channel.
     */
    showOutput(): void;
    dispose(): void;
}
//# sourceMappingURL=backendManager.d.ts.map