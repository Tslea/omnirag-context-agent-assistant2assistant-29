/**
 * Unit Tests for EventBus
 * 
 * Tests the publish/subscribe event system used for
 * decoupled communication between extension components.
 * 
 * Run: npm test -- --testPathPattern=eventBus
 */

import { EventBus, EventType } from '../events/eventBus';

describe('EventBus', () => {
  let eventBus: EventBus;

  beforeEach(() => {
    // Create fresh EventBus instance for each test
    eventBus = new EventBus();
  });

  afterEach(() => {
    // Dispose to clean up subscriptions
    eventBus.dispose();
  });

  describe('subscribe', () => {
    it('should register a subscriber for an event type', () => {
      const callback = jest.fn();
      
      eventBus.subscribe(EventType.ChatMessage, callback);
      
      // Subscriber should be registered (tested by publish working)
      eventBus.publish(EventType.ChatMessage, { content: 'test' });
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should return a disposable that removes the subscription', () => {
      const callback = jest.fn();
      
      const subscription = eventBus.subscribe(EventType.ChatMessage, callback);
      subscription.dispose();
      
      eventBus.publish(EventType.ChatMessage, { content: 'test' });
      expect(callback).not.toHaveBeenCalled();
    });

    it('should allow multiple subscribers for the same event', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      eventBus.subscribe(EventType.ChatMessage, callback1);
      eventBus.subscribe(EventType.ChatMessage, callback2);
      
      eventBus.publish(EventType.ChatMessage, { content: 'test' });
      
      expect(callback1).toHaveBeenCalledTimes(1);
      expect(callback2).toHaveBeenCalledTimes(1);
    });

    it('should isolate subscriptions by event type', () => {
      const chatCallback = jest.fn();
      const errorCallback = jest.fn();
      
      eventBus.subscribe(EventType.ChatMessage, chatCallback);
      eventBus.subscribe(EventType.Error, errorCallback);
      
      eventBus.publish(EventType.ChatMessage, { content: 'test' });
      
      expect(chatCallback).toHaveBeenCalledTimes(1);
      expect(errorCallback).not.toHaveBeenCalled();
    });
  });

  describe('publish', () => {
    it('should call subscriber with the published data', () => {
      const callback = jest.fn();
      const testData = { content: 'Hello, World!', sender: 'user' };
      
      eventBus.subscribe(EventType.ChatMessage, callback);
      eventBus.publish(EventType.ChatMessage, testData);
      
      expect(callback).toHaveBeenCalledWith(testData);
    });

    it('should handle publishing to event with no subscribers', () => {
      // Should not throw
      expect(() => {
        eventBus.publish(EventType.ChatMessage, { content: 'test' });
      }).not.toThrow();
    });

    it('should call subscribers in order of registration', () => {
      const order: number[] = [];
      
      eventBus.subscribe(EventType.ChatMessage, () => { order.push(1); });
      eventBus.subscribe(EventType.ChatMessage, () => { order.push(2); });
      eventBus.subscribe(EventType.ChatMessage, () => { order.push(3); });
      
      eventBus.publish(EventType.ChatMessage, {});
      
      expect(order).toEqual([1, 2, 3]);
    });

    it('should continue calling other subscribers if one throws', () => {
      const callback1 = jest.fn();
      const errorCallback = jest.fn(() => {
        throw new Error('Subscriber error');
      });
      const callback2 = jest.fn();
      
      eventBus.subscribe(EventType.ChatMessage, callback1);
      eventBus.subscribe(EventType.ChatMessage, errorCallback);
      eventBus.subscribe(EventType.ChatMessage, callback2);
      
      // Should not throw, and should call remaining subscribers
      expect(() => {
        eventBus.publish(EventType.ChatMessage, {});
      }).not.toThrow();
      
      expect(callback1).toHaveBeenCalled();
      expect(callback2).toHaveBeenCalled();
    });
  });

  describe('once', () => {
    it('should only trigger callback once then auto-unsubscribe', () => {
      const callback = jest.fn();
      
      eventBus.once(EventType.ChatMessage, callback);
      
      eventBus.publish(EventType.ChatMessage, { content: 'first' });
      eventBus.publish(EventType.ChatMessage, { content: 'second' });
      
      expect(callback).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledWith({ content: 'first' });
    });

    it('should return a disposable that can cancel before trigger', () => {
      const callback = jest.fn();
      
      const subscription = eventBus.once(EventType.ChatMessage, callback);
      subscription.dispose();
      
      eventBus.publish(EventType.ChatMessage, { content: 'test' });
      
      expect(callback).not.toHaveBeenCalled();
    });
  });

  describe('dispose', () => {
    it('should remove all subscriptions', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      eventBus.subscribe(EventType.ChatMessage, callback1);
      eventBus.subscribe(EventType.Error, callback2);
      
      eventBus.dispose();
      
      eventBus.publish(EventType.ChatMessage, {});
      eventBus.publish(EventType.Error, {});
      
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).not.toHaveBeenCalled();
    });

    it('should be safe to call dispose multiple times', () => {
      expect(() => {
        eventBus.dispose();
        eventBus.dispose();
      }).not.toThrow();
    });
  });

  describe('hasSubscribers', () => {
    it('should return false when no subscribers exist', () => {
      expect(eventBus.hasSubscribers(EventType.ChatMessage)).toBe(false);
    });

    it('should return true when subscribers exist', () => {
      eventBus.subscribe(EventType.ChatMessage, jest.fn());
      
      expect(eventBus.hasSubscribers(EventType.ChatMessage)).toBe(true);
    });

    it('should return false after subscriber is disposed', () => {
      const subscription = eventBus.subscribe(EventType.ChatMessage, jest.fn());
      
      subscription.dispose();
      
      expect(eventBus.hasSubscribers(EventType.ChatMessage)).toBe(false);
    });
  });

  describe('getSubscriberCount', () => {
    it('should return 0 when no subscribers', () => {
      expect(eventBus.getSubscriberCount(EventType.ChatMessage)).toBe(0);
    });

    it('should return correct count', () => {
      eventBus.subscribe(EventType.ChatMessage, jest.fn());
      eventBus.subscribe(EventType.ChatMessage, jest.fn());
      eventBus.subscribe(EventType.Error, jest.fn());
      
      expect(eventBus.getSubscriberCount(EventType.ChatMessage)).toBe(2);
      expect(eventBus.getSubscriberCount(EventType.Error)).toBe(1);
    });
  });
});

describe('EventType', () => {
  it('should have all required event types', () => {
    // Verify core event types exist
    expect(EventType.ChatMessage).toBeDefined();
    expect(EventType.AgentResponse).toBeDefined();
    expect(EventType.StreamChunk).toBeDefined();
    expect(EventType.Error).toBeDefined();
    expect(EventType.BackendConnected).toBeDefined();
    expect(EventType.BackendDisconnected).toBeDefined();
  });
});
