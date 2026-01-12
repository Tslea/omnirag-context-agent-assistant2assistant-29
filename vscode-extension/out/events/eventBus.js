"use strict";
/**
 * Event Bus
 *
 * Internal pub/sub system for extension components.
 * Decouples components and enables loose coupling.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Events = exports.EventBus = exports.EventType = void 0;
/**
 * Strongly-typed event types for the extension.
 */
var EventType;
(function (EventType) {
    // Chat events
    EventType["ChatMessage"] = "chat:message";
    EventType["AgentResponse"] = "agent:response";
    EventType["StreamChunk"] = "stream:chunk";
    EventType["StreamStart"] = "stream:start";
    EventType["StreamEnd"] = "stream:end";
    // Error events
    EventType["Error"] = "error";
    // Backend events
    EventType["BackendConnected"] = "backend:connected";
    EventType["BackendDisconnected"] = "backend:disconnected";
    EventType["BackendStarting"] = "backend:starting";
    EventType["BackendError"] = "backend:error";
    // Agent events
    EventType["AgentSelected"] = "agent:selected";
    EventType["AgentListUpdated"] = "agent:list:updated";
    // UI events
    EventType["ViewReady"] = "view:ready";
    EventType["SettingsChanged"] = "settings:changed";
})(EventType || (exports.EventType = EventType = {}));
/**
 * Simple event bus for internal extension communication.
 */
class EventBus {
    listeners = new Map();
    subscriptions = [];
    /**
     * Subscribe to an event.
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
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
    subscribe(event, callback) {
        return this.on(event, callback);
    }
    /**
     * Publish an event (alias for emit, but synchronous).
     */
    publish(event, data) {
        const listeners = this.listeners.get(event);
        if (!listeners) {
            return;
        }
        for (const callback of listeners) {
            try {
                callback(data);
            }
            catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
                // Continue to other subscribers even if one throws
            }
        }
    }
    /**
     * Subscribe to an event, but only trigger once.
     */
    once(event, callback) {
        const wrapper = (data) => {
            this.off(event, wrapper);
            callback(data);
        };
        return this.on(event, wrapper);
    }
    /**
     * Unsubscribe from an event.
     */
    off(event, callback) {
        const listeners = this.listeners.get(event);
        if (listeners) {
            listeners.delete(callback);
        }
    }
    /**
     * Emit an event to all subscribers.
     */
    async emit(event, data) {
        const listeners = this.listeners.get(event);
        if (!listeners) {
            return;
        }
        const promises = [];
        for (const callback of listeners) {
            try {
                const result = callback(data);
                if (result instanceof Promise) {
                    promises.push(result);
                }
            }
            catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
            }
        }
        await Promise.allSettled(promises);
    }
    /**
     * Get the number of listeners for an event.
     */
    listenerCount(event) {
        return this.listeners.get(event)?.size ?? 0;
    }
    /**
     * Check if an event has any subscribers.
     */
    hasSubscribers(event) {
        return (this.listeners.get(event)?.size ?? 0) > 0;
    }
    /**
     * Get subscriber count for an event (alias for listenerCount).
     */
    getSubscriberCount(event) {
        return this.listenerCount(event);
    }
    /**
     * Remove all listeners for an event.
     */
    removeAllListeners(event) {
        if (event) {
            this.listeners.delete(event);
        }
        else {
            this.listeners.clear();
        }
    }
    /**
     * Dispose of all subscriptions.
     */
    dispose() {
        this.listeners.clear();
        this.subscriptions = [];
    }
}
exports.EventBus = EventBus;
/**
 * Common event types used in the extension.
 */
exports.Events = {
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
};
//# sourceMappingURL=eventBus.js.map