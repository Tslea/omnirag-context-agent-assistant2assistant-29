/**
 * WebSocket Client
 * 
 * Handles WebSocket communication with the Python backend.
 */

import WebSocket from 'ws';

export interface Message {
    type: string;
    data: any;
    id?: string;
    timestamp?: string;
}

export interface WebSocketCallbacks {
    onOpen?: () => void;
    onClose?: () => void;
    onError?: (error: string) => void;
    onMessage?: (message: Message) => void;
}

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private url: string;
    private callbacks: WebSocketCallbacks;
    private messageQueue: Message[] = [];
    private pendingRequests: Map<string, {
        resolve: (value: any) => void;
        reject: (reason: any) => void;
    }> = new Map();

    constructor(url: string, callbacks: WebSocketCallbacks = {}) {
        this.url = url;
        this.callbacks = callbacks;
    }

    /**
     * Connect to the WebSocket server.
     */
    async connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);

                this.ws.on('open', () => {
                    this.callbacks.onOpen?.();
                    this.flushMessageQueue();
                    resolve();
                });

                this.ws.on('close', () => {
                    this.callbacks.onClose?.();
                });

                this.ws.on('error', (error) => {
                    this.callbacks.onError?.(error.message);
                    reject(error);
                });

                this.ws.on('message', (data) => {
                    try {
                        const message: Message = JSON.parse(data.toString());
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Failed to parse message:', error);
                    }
                });

                // Timeout for connection
                setTimeout(() => {
                    if (this.ws?.readyState !== WebSocket.OPEN) {
                        reject(new Error('Connection timeout'));
                    }
                }, 10000);

            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Handle incoming messages.
     */
    private handleMessage(message: Message): void {
        // Check if this is a response to a pending request
        if (message.id && this.pendingRequests.has(message.id)) {
            const pending = this.pendingRequests.get(message.id)!;
            this.pendingRequests.delete(message.id);

            if (message.type === 'error') {
                pending.reject(message.data);
            } else {
                pending.resolve(message.data);
            }
            return;
        }

        // Otherwise, pass to callback
        this.callbacks.onMessage?.(message);
    }

    /**
     * Send a message to the server.
     */
    async send(message: Omit<Message, 'timestamp'>): Promise<void> {
        const fullMessage: Message = {
            ...message,
            timestamp: new Date().toISOString(),
        };

        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            // Queue message for later
            this.messageQueue.push(fullMessage);
            return;
        }

        return new Promise((resolve, reject) => {
            this.ws!.send(JSON.stringify(fullMessage), (error) => {
                if (error) {
                    reject(error);
                } else {
                    resolve();
                }
            });
        });
    }

    /**
     * Send a message and wait for a response.
     */
    async request(type: string, data: any, timeout: number = 30000): Promise<any> {
        const id = this.generateId();
        
        const promise = new Promise((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });

            // Set timeout
            setTimeout(() => {
                if (this.pendingRequests.has(id)) {
                    this.pendingRequests.delete(id);
                    reject(new Error('Request timeout'));
                }
            }, timeout);
        });

        await this.send({ type, data, id });
        return promise;
    }

    /**
     * Flush queued messages after reconnection.
     */
    private flushMessageQueue(): void {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift()!;
            this.send(message).catch(console.error);
        }
    }

    /**
     * Generate a unique message ID.
     */
    private generateId(): string {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Check if connected.
     */
    get connected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    /**
     * Disconnect from the server.
     */
    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.pendingRequests.clear();
        this.messageQueue = [];
    }
}
