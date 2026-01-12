/**
 * Event Bus
 * 
 * Internal pub/sub system for extension components.
 * Decouples components and enables loose coupling.
 */

import * as vscode from 'vscode';

export type EventCallback<T = any> = (data: T) => void | Promise<void>;

interface EventSubscription {
    event: string;
    callback: EventCallback;
}

/**
 * Strongly-typed event types for the extension.
 */
export enum EventType {
    // Chat events
    ChatMessage = 'chat:message',
    AgentResponse = 'agent:response',
    StreamChunk = 'stream:chunk',
    StreamStart = 'stream:start',
    StreamEnd = 'stream:end',
    
    // Error events
    Error = 'error',
    
    // Backend events
    BackendConnected = 'backend:connected',
    BackendDisconnected = 'backend:disconnected',
    BackendStarting = 'backend:starting',
    BackendError = 'backend:error',
    
    // Agent events
    AgentSelected = 'agent:selected',
    AgentListUpdated = 'agent:list:updated',
    
    // UI events
    ViewReady = 'view:ready',
    SettingsChanged = 'settings:changed',
}

/**
 * Simple event bus for internal extension communication.
 */
export class EventBus implements vscode.Disposable {
    private listeners: Map<string, Set<EventCallback>> = new Map();
    private subscriptions: EventSubscription[] = [];

    /**
     * Subscribe to an event.
     */
    on<T = any>(event: string, callback: EventCallback<T>): vscode.Disposable {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        
        this.listeners.get(event)!.add(callback);
        this.subscriptions.push({ event, callback });

        return {
            dispose: () => {
                this.off(event, callback);
            }
        };
    }

    /**
     * Subscribe to an event (alias for on).
     */
    subscribe<T = any>(event: EventType | string, callback: EventCallback<T>): vscode.Disposable {
        return this.on(event, callback);
    }

    /**
     * Publish an event (alias for emit, but synchronous).
     */
    publish<T = any>(event: EventType | string, data?: T): void {
        const listeners = this.listeners.get(event);
        if (!listeners) {
            return;
        }

        for (const callback of listeners) {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
                // Continue to other subscribers even if one throws
            }
        }
    }

    /**
     * Subscribe to an event, but only trigger once.
     */
    once<T = any>(event: string, callback: EventCallback<T>): vscode.Disposable {
        const wrapper: EventCallback<T> = (data) => {
            this.off(event, wrapper);
            callback(data);
        };
        
        return this.on(event, wrapper);
    }

    /**
     * Unsubscribe from an event.
     */
    off(event: string, callback: EventCallback): void {
        const listeners = this.listeners.get(event);
        if (listeners) {
            listeners.delete(callback);
        }
    }

    /**
     * Emit an event to all subscribers.
     */
    async emit<T = any>(event: string, data?: T): Promise<void> {
        const listeners = this.listeners.get(event);
        if (!listeners) {
            return;
        }

        const promises: Promise<void>[] = [];
        
        for (const callback of listeners) {
            try {
                const result = callback(data);
                if (result instanceof Promise) {
                    promises.push(result);
                }
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
            }
        }

        await Promise.allSettled(promises);
    }

    /**
     * Get the number of listeners for an event.
     */
    listenerCount(event: string): number {
        return this.listeners.get(event)?.size ?? 0;
    }

    /**
     * Check if an event has any subscribers.
     */
    hasSubscribers(event: EventType | string): boolean {
        return (this.listeners.get(event)?.size ?? 0) > 0;
    }

    /**
     * Get subscriber count for an event (alias for listenerCount).
     */
    getSubscriberCount(event: EventType | string): number {
        return this.listenerCount(event);
    }

    /**
     * Remove all listeners for an event.
     */
    removeAllListeners(event?: string): void {
        if (event) {
            this.listeners.delete(event);
        } else {
            this.listeners.clear();
        }
    }

    /**
     * Dispose of all subscriptions.
     */
    dispose(): void {
        this.listeners.clear();
        this.subscriptions = [];
    }
}

/**
 * Common event types used in the extension.
 */
export const Events = {
    // Backend events
    BACKEND_STARTING: 'backend:starting',
    BACKEND_CONNECTED: 'backend:connected',
    BACKEND_DISCONNECTED: 'backend:disconnected',
    BACKEND_ERROR: 'backend:error',

    // Chat events
    CHAT_MESSAGE_SENT: 'chat:message:sent',
    CHAT_MESSAGE_RECEIVED: 'chat:message:received',
    CHAT_STREAM_START: 'chat:stream:start',
    CHAT_STREAM_CHUNK: 'chat:stream:chunk',
    CHAT_STREAM_END: 'chat:stream:end',
    CHAT_ERROR: 'chat:error',

    // Agent events
    AGENT_SELECTED: 'agent:selected',
    AGENT_LIST_UPDATED: 'agent:list:updated',
    AGENT_STATUS_CHANGED: 'agent:status:changed',

    // UI events
    VIEW_READY: 'view:ready',
    SETTINGS_CHANGED: 'settings:changed',
} as const;
