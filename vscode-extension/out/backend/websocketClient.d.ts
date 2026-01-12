/**
 * WebSocket Client
 *
 * Handles WebSocket communication with the Python backend.
 */
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
export declare class WebSocketClient {
    private ws;
    private url;
    private callbacks;
    private messageQueue;
    private pendingRequests;
    constructor(url: string, callbacks?: WebSocketCallbacks);
    /**
     * Connect to the WebSocket server.
     */
    connect(): Promise<void>;
    /**
     * Handle incoming messages.
     */
    private handleMessage;
    /**
     * Send a message to the server.
     */
    send(message: Omit<Message, 'timestamp'>): Promise<void>;
    /**
     * Send a message and wait for a response.
     */
    request(type: string, data: any, timeout?: number): Promise<any>;
    /**
     * Flush queued messages after reconnection.
     */
    private flushMessageQueue;
    /**
     * Generate a unique message ID.
     */
    private generateId;
    /**
     * Check if connected.
     */
    get connected(): boolean;
    /**
     * Disconnect from the server.
     */
    disconnect(): void;
}
//# sourceMappingURL=websocketClient.d.ts.map