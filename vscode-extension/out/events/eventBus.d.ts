/**
 * Event Bus
 *
 * Internal pub/sub system for extension components.
 * Decouples components and enables loose coupling.
 */
import * as vscode from 'vscode';
export type EventCallback<T = any> = (data: T) => void | Promise<void>;
/**
 * Strongly-typed event types for the extension.
 */
export declare enum EventType {
    ChatMessage = "chat:message",
    AgentResponse = "agent:response",
    StreamChunk = "stream:chunk",
    StreamStart = "stream:start",
    StreamEnd = "stream:end",
    Error = "error",
    BackendConnected = "backend:connected",
    BackendDisconnected = "backend:disconnected",
    BackendStarting = "backend:starting",
    BackendError = "backend:error",
    AgentSelected = "agent:selected",
    AgentListUpdated = "agent:list:updated",
    ViewReady = "view:ready",
    SettingsChanged = "settings:changed"
}
/**
 * Simple event bus for internal extension communication.
 */
export declare class EventBus implements vscode.Disposable {
    private listeners;
    private subscriptions;
    /**
     * Subscribe to an event.
     */
    on<T = any>(event: string, callback: EventCallback<T>): vscode.Disposable;
    /**
     * Subscribe to an event (alias for on).
     */
    subscribe<T = any>(event: EventType | string, callback: EventCallback<T>): vscode.Disposable;
    /**
     * Publish an event (alias for emit, but synchronous).
     */
    publish<T = any>(event: EventType | string, data?: T): void;
    /**
     * Subscribe to an event, but only trigger once.
     */
    once<T = any>(event: string, callback: EventCallback<T>): vscode.Disposable;
    /**
     * Unsubscribe from an event.
     */
    off(event: string, callback: EventCallback): void;
    /**
     * Emit an event to all subscribers.
     */
    emit<T = any>(event: string, data?: T): Promise<void>;
    /**
     * Get the number of listeners for an event.
     */
    listenerCount(event: string): number;
    /**
     * Check if an event has any subscribers.
     */
    hasSubscribers(event: EventType | string): boolean;
    /**
     * Get subscriber count for an event (alias for listenerCount).
     */
    getSubscriberCount(event: EventType | string): number;
    /**
     * Remove all listeners for an event.
     */
    removeAllListeners(event?: string): void;
    /**
     * Dispose of all subscriptions.
     */
    dispose(): void;
}
/**
 * Common event types used in the extension.
 */
export declare const Events: {
    readonly BACKEND_STARTING: "backend:starting";
    readonly BACKEND_CONNECTED: "backend:connected";
    readonly BACKEND_DISCONNECTED: "backend:disconnected";
    readonly BACKEND_ERROR: "backend:error";
    readonly CHAT_MESSAGE_SENT: "chat:message:sent";
    readonly CHAT_MESSAGE_RECEIVED: "chat:message:received";
    readonly CHAT_STREAM_START: "chat:stream:start";
    readonly CHAT_STREAM_CHUNK: "chat:stream:chunk";
    readonly CHAT_STREAM_END: "chat:stream:end";
    readonly CHAT_ERROR: "chat:error";
    readonly AGENT_SELECTED: "agent:selected";
    readonly AGENT_LIST_UPDATED: "agent:list:updated";
    readonly AGENT_STATUS_CHANGED: "agent:status:changed";
    readonly VIEW_READY: "view:ready";
    readonly SETTINGS_CHANGED: "settings:changed";
};
//# sourceMappingURL=eventBus.d.ts.map