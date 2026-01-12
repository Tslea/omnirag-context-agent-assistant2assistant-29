"use strict";
/**
 * Unit Tests for WebSocket Client
 *
 * Tests the WebSocket communication between extension and backend.
 *
 * Run: npm test -- --testPathPattern=websocketClient
 */
Object.defineProperty(exports, "__esModule", { value: true });
const websocketClient_1 = require("../backend/websocketClient");
// Mock the 'ws' module
jest.mock('ws', () => {
    return jest.fn().mockImplementation((url) => {
        const instance = {
            url,
            readyState: 0, // CONNECTING
            on: jest.fn((event, handler) => {
                instance[`_${event}Handler`] = handler;
            }),
            send: jest.fn((_data, callback) => {
                if (callback) {
                    callback();
                }
            }),
            close: jest.fn(),
            // Test helpers
            simulateOpen: () => {
                instance.readyState = 1; // OPEN
                instance._openHandler?.();
            },
            simulateClose: () => {
                instance.readyState = 3; // CLOSED
                instance._closeHandler?.();
            },
            simulateMessage: (data) => {
                const buffer = Buffer.from(JSON.stringify(data));
                instance._messageHandler?.(buffer);
            },
            simulateError: (error) => {
                instance._errorHandler?.(error);
            },
        };
        return instance;
    });
});
// Get the mocked WebSocket constructor
const MockWebSocket = require('ws');
describe('WebSocketClient', () => {
    let client;
    let callbacks;
    let mockWsInstance;
    beforeEach(() => {
        // Reset mock
        MockWebSocket.mockClear();
        // Create callbacks
        callbacks = {
            onOpen: jest.fn(),
            onClose: jest.fn(),
            onError: jest.fn(),
            onMessage: jest.fn(),
        };
        client = new websocketClient_1.WebSocketClient('ws://localhost:8765', callbacks);
    });
    afterEach(() => {
        client.disconnect();
    });
    describe('connect', () => {
        it('should create WebSocket connection with correct URL', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            expect(MockWebSocket).toHaveBeenCalledWith('ws://localhost:8765');
        });
        it('should call onOpen callback on successful connection', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            expect(callbacks.onOpen).toHaveBeenCalled();
        });
        it('should update connected property on successful connection', async () => {
            expect(client.connected).toBe(false);
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            expect(client.connected).toBe(true);
        });
        it('should reject if connection fails', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateError(new Error('Connection failed'));
            await expect(connectPromise).rejects.toThrow('Connection failed');
        });
    });
    describe('disconnect', () => {
        it('should close WebSocket connection', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            client.disconnect();
            expect(mockWsInstance.close).toHaveBeenCalled();
        });
        it('should call onClose callback', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            client.disconnect();
            mockWsInstance.simulateClose();
            expect(callbacks.onClose).toHaveBeenCalled();
        });
    });
    describe('send', () => {
        it('should send JSON message through WebSocket', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            const message = { type: 'chat', data: { content: 'Hello' } };
            await client.send(message);
            expect(mockWsInstance.send).toHaveBeenCalledWith(expect.stringContaining('"type":"chat"'), expect.any(Function));
        });
        it('should add timestamp to message', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            const message = { type: 'chat', data: { content: 'Hello' } };
            await client.send(message);
            const sentData = JSON.parse(mockWsInstance.send.mock.calls[0][0]);
            expect(sentData.timestamp).toBeDefined();
        });
        it('should queue message if not connected', async () => {
            const message = { type: 'test', data: {} };
            await client.send(message);
            // Message should be queued, not sent immediately
            expect(mockWsInstance?.send).toBeUndefined();
        });
    });
    describe('message handling', () => {
        it('should call onMessage callback for incoming messages', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            const incomingMessage = {
                type: 'chat_response',
                data: { content: 'Hello from backend' },
            };
            mockWsInstance.simulateMessage(incomingMessage);
            expect(callbacks.onMessage).toHaveBeenCalledWith(expect.objectContaining({
                type: 'chat_response',
                data: { content: 'Hello from backend' },
            }));
        });
        it('should handle stream_chunk messages', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            const streamMessage = {
                type: 'stream_chunk',
                data: { chunk: 'partial response' },
            };
            mockWsInstance.simulateMessage(streamMessage);
            expect(callbacks.onMessage).toHaveBeenCalledWith(expect.objectContaining({
                type: 'stream_chunk',
            }));
        });
        it('should handle error messages', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            const errorMessage = {
                type: 'error',
                data: { message: 'Something went wrong' },
            };
            mockWsInstance.simulateMessage(errorMessage);
            expect(callbacks.onMessage).toHaveBeenCalledWith(expect.objectContaining({
                type: 'error',
            }));
        });
    });
    describe('request/response', () => {
        it('should resolve request when matching response received', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            // Start a request
            const requestPromise = client.request('get_agents', {});
            // Get the sent message to extract the ID
            const sentData = JSON.parse(mockWsInstance.send.mock.calls[0][0]);
            // Simulate response with matching ID
            mockWsInstance.simulateMessage({
                type: 'response',
                id: sentData.id,
                data: { agents: ['agent1', 'agent2'] },
            });
            const result = await requestPromise;
            expect(result).toEqual({ agents: ['agent1', 'agent2'] });
        });
    });
    describe('disconnect behavior', () => {
        it('should clear pending requests on disconnect', async () => {
            const connectPromise = client.connect();
            mockWsInstance = MockWebSocket.mock.results[0].value;
            mockWsInstance.simulateOpen();
            await connectPromise;
            client.disconnect();
            // Should not throw
            expect(mockWsInstance.close).toHaveBeenCalled();
        });
        it('should be safe to call disconnect multiple times', () => {
            expect(() => {
                client.disconnect();
                client.disconnect();
            }).not.toThrow();
        });
    });
});
//# sourceMappingURL=websocketClient.test.js.map