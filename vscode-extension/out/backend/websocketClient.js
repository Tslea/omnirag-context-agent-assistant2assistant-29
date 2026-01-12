"use strict";
/**
 * WebSocket Client
 *
 * Handles WebSocket communication with the Python backend.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WebSocketClient = void 0;
const ws_1 = __importDefault(require("ws"));
class WebSocketClient {
    ws = null;
    url;
    callbacks;
    messageQueue = [];
    pendingRequests = new Map();
    constructor(url, callbacks = {}) {
        this.url = url;
        this.callbacks = callbacks;
    }
    /**
     * Connect to the WebSocket server.
     */
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new ws_1.default(this.url);
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
                        const message = JSON.parse(data.toString());
                        this.handleMessage(message);
                    }
                    catch (error) {
                        console.error('Failed to parse message:', error);
                    }
                });
                // Timeout for connection
                setTimeout(() => {
                    if (this.ws?.readyState !== ws_1.default.OPEN) {
                        reject(new Error('Connection timeout'));
                    }
                }, 10000);
            }
            catch (error) {
                reject(error);
            }
        });
    }
    /**
     * Handle incoming messages.
     */
    handleMessage(message) {
        // Check if this is a response to a pending request
        if (message.id && this.pendingRequests.has(message.id)) {
            const pending = this.pendingRequests.get(message.id);
            this.pendingRequests.delete(message.id);
            if (message.type === 'error') {
                pending.reject(message.data);
            }
            else {
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
    async send(message) {
        const fullMessage = {
            ...message,
            timestamp: new Date().toISOString(),
        };
        if (!this.ws || this.ws.readyState !== ws_1.default.OPEN) {
            // Queue message for later
            this.messageQueue.push(fullMessage);
            return;
        }
        return new Promise((resolve, reject) => {
            this.ws.send(JSON.stringify(fullMessage), (error) => {
                if (error) {
                    reject(error);
                }
                else {
                    resolve();
                }
            });
        });
    }
    /**
     * Send a message and wait for a response.
     */
    async request(type, data, timeout = 30000) {
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
    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message).catch(console.error);
        }
    }
    /**
     * Generate a unique message ID.
     */
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    /**
     * Check if connected.
     */
    get connected() {
        return this.ws?.readyState === ws_1.default.OPEN;
    }
    /**
     * Disconnect from the server.
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.pendingRequests.clear();
        this.messageQueue = [];
    }
}
exports.WebSocketClient = WebSocketClient;
//# sourceMappingURL=websocketClient.js.map