"use strict";
/**
 * Chat View Provider
 *
 * Webview panel for the chat interface.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatViewProvider = void 0;
const eventBus_1 = require("../events/eventBus");
class ChatViewProvider {
    static viewType = 'omni.chatView';
    view;
    extensionUri;
    backendManager;
    eventBus;
    currentAgent = 'assistant';
    messageHistory = [];
    constructor(extensionUri, backendManager, eventBus) {
        this.extensionUri = extensionUri;
        this.backendManager = backendManager;
        this.eventBus = eventBus;
        this.setupEventListeners();
    }
    setupEventListeners() {
        // Handle incoming chat messages
        this.eventBus.on(eventBus_1.Events.CHAT_MESSAGE_RECEIVED, (data) => {
            this.addMessage('assistant', data.content);
        });
        // Handle streaming
        this.eventBus.on(eventBus_1.Events.CHAT_STREAM_START, () => {
            this.postMessage({ type: 'streamStart' });
        });
        this.eventBus.on(eventBus_1.Events.CHAT_STREAM_CHUNK, (data) => {
            this.postMessage({ type: 'streamChunk', content: data.content });
        });
        this.eventBus.on(eventBus_1.Events.CHAT_STREAM_END, () => {
            this.postMessage({ type: 'streamEnd' });
        });
        // Handle errors
        this.eventBus.on(eventBus_1.Events.CHAT_ERROR, (data) => {
            this.postMessage({ type: 'error', message: data.message });
        });
        // Handle agent selection
        this.eventBus.on(eventBus_1.Events.AGENT_SELECTED, (data) => {
            this.currentAgent = data.agentId;
            this.postMessage({ type: 'agentChanged', agentId: data.agentId });
        });
        // Handle connection status
        this.eventBus.on(eventBus_1.Events.BACKEND_CONNECTED, () => {
            this.postMessage({ type: 'connected' });
        });
        this.eventBus.on(eventBus_1.Events.BACKEND_DISCONNECTED, () => {
            this.postMessage({ type: 'disconnected' });
        });
    }
    resolveWebviewView(webviewView, _context, _token) {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri],
        };
        webviewView.webview.html = this.getHtmlContent(webviewView.webview);
        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'sendMessage':
                    await this.handleSendMessage(message.content);
                    break;
                case 'selectAgent':
                    await this.backendManager.selectAgent(message.agentId);
                    break;
                case 'clearHistory':
                    this.clearHistory();
                    break;
                case 'ready':
                    this.eventBus.emit(eventBus_1.Events.VIEW_READY);
                    this.sendInitialState();
                    break;
            }
        });
    }
    async handleSendMessage(content) {
        if (!content.trim()) {
            return;
        }
        // Add user message to history
        this.addMessage('user', content);
        try {
            await this.backendManager.sendChatMessage(content, this.currentAgent);
        }
        catch (error) {
            this.postMessage({
                type: 'error',
                message: `Failed to send message: ${error}`,
            });
        }
    }
    addMessage(role, content) {
        this.messageHistory.push({ role, content });
        this.postMessage({
            type: 'addMessage',
            role,
            content,
        });
    }
    clearHistory() {
        this.messageHistory = [];
        this.postMessage({ type: 'clearHistory' });
    }
    sendInitialState() {
        // Send connection status
        this.postMessage({
            type: this.backendManager.connected ? 'connected' : 'disconnected',
        });
        // Send current agent
        this.postMessage({
            type: 'agentChanged',
            agentId: this.currentAgent,
        });
        // Send existing message history
        for (const msg of this.messageHistory) {
            this.postMessage({
                type: 'addMessage',
                role: msg.role,
                content: msg.content,
            });
        }
    }
    postMessage(message) {
        this.view?.webview.postMessage(message);
    }
    /**
     * Add a message from external command (e.g., explain code).
     */
    async sendMessage(content) {
        await this.handleSendMessage(content);
    }
    getHtmlContent(webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src ${webview.cspSource} 'unsafe-inline';">
    <title>OMNI Chat</title>
    <style>
        :root {
            --message-spacing: 12px;
            --border-radius: 6px;
            --transition-speed: 0.2s;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.5;
        }
        
        /* Header */
        .header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--vscode-sideBar-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--vscode-sideBar-background);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .agent-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            background-color: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            border-radius: 10px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--vscode-testing-iconFailed);
            transition: background-color var(--transition-speed);
        }
        
        .status-dot.connected {
            background-color: var(--vscode-testing-iconPassed);
        }
        
        .status-dot.connecting {
            background-color: var(--vscode-charts-yellow);
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Welcome Screen */
        .welcome {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            text-align: center;
            color: var(--vscode-descriptionForeground);
        }
        
        .welcome-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.6;
        }
        
        .welcome h2 {
            font-size: 16px;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--vscode-foreground);
        }
        
        .welcome p {
            font-size: 13px;
            max-width: 280px;
        }
        
        .welcome.hidden {
            display: none;
        }
        
        /* Messages Container */
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: var(--message-spacing);
            scroll-behavior: smooth;
        }
        
        .messages:empty + .welcome {
            display: flex;
        }
        
        .messages:not(:empty) + .welcome {
            display: none;
        }
        
        /* Message Bubble */
        .message {
            margin-bottom: var(--message-spacing);
            padding: 10px 14px;
            border-radius: var(--border-radius);
            max-width: 90%;
            word-wrap: break-word;
            animation: fadeIn 0.2s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            margin-left: auto;
            border-bottom-right-radius: 2px;
        }
        
        .message.assistant {
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-sideBar-border);
            border-bottom-left-radius: 2px;
        }
        
        .message.error {
            background-color: var(--vscode-inputValidation-errorBackground);
            border: 1px solid var(--vscode-inputValidation-errorBorder);
            color: var(--vscode-errorForeground);
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        .message.user .message-header {
            color: var(--vscode-button-foreground);
            opacity: 0.8;
        }
        
        /* Code Blocks */
        .message pre {
            background-color: var(--vscode-textCodeBlock-background);
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 10px 0;
            position: relative;
        }
        
        .message code {
            font-family: var(--vscode-editor-font-family);
            font-size: calc(var(--vscode-editor-font-size) - 1px);
        }
        
        .message p code {
            background-color: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
        }
        
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 12px;
            background-color: var(--vscode-editor-background);
            border-bottom: 1px solid var(--vscode-sideBar-border);
            border-radius: 4px 4px 0 0;
            margin-bottom: -4px;
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        .copy-btn {
            background: none;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 2px 6px;
            font-size: 11px;
            border-radius: 3px;
            opacity: 0.7;
            transition: opacity var(--transition-speed);
        }
        
        .copy-btn:hover {
            opacity: 1;
            background-color: var(--vscode-toolbar-hoverBackground);
        }
        
        .copy-btn.copied {
            color: var(--vscode-testing-iconPassed);
        }
        
        /* Lists */
        .message ul, .message ol {
            margin: 8px 0;
            padding-left: 20px;
        }
        
        .message li {
            margin: 4px 0;
        }
        
        /* Typing Indicator */
        .typing-indicator {
            display: none;
            padding: 8px 12px;
            color: var(--vscode-descriptionForeground);
            font-size: 12px;
            align-items: center;
            gap: 8px;
        }
        
        .typing-indicator.visible {
            display: flex;
        }
        
        .typing-dots {
            display: flex;
            gap: 4px;
        }
        
        .typing-dots span {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--vscode-descriptionForeground);
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        
        /* Input Area */
        .input-container {
            padding: 12px;
            border-top: 1px solid var(--vscode-sideBar-border);
            background-color: var(--vscode-sideBar-background);
        }
        
        .input-wrapper {
            display: flex;
            gap: 8px;
            align-items: flex-end;
        }
        
        textarea {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid var(--vscode-input-border);
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: var(--border-radius);
            font-family: inherit;
            font-size: inherit;
            resize: none;
            min-height: 40px;
            max-height: 150px;
            line-height: 1.4;
            transition: border-color var(--transition-speed);
        }
        
        textarea:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        
        textarea::placeholder {
            color: var(--vscode-input-placeholderForeground);
        }
        
        textarea:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .btn {
            padding: 8px 16px;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            font-family: inherit;
            font-size: 13px;
            font-weight: 500;
            transition: background-color var(--transition-speed);
            display: flex;
            align-items: center;
            gap: 6px;
            min-height: 36px;
        }
        
        .btn:hover:not(:disabled) {
            background-color: var(--vscode-button-hoverBackground);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-icon {
            background: none;
            border: none;
            padding: 6px;
            border-radius: 4px;
            cursor: pointer;
            color: var(--vscode-foreground);
            opacity: 0.7;
        }
        
        .btn-icon:hover {
            opacity: 1;
            background-color: var(--vscode-toolbar-hoverBackground);
        }
        
        /* Offline Banner */
        .offline-banner {
            display: none;
            padding: 8px 12px;
            background-color: var(--vscode-inputValidation-warningBackground);
            border-bottom: 1px solid var(--vscode-inputValidation-warningBorder);
            color: var(--vscode-inputValidation-warningForeground);
            font-size: 12px;
            text-align: center;
        }
        
        .offline-banner.visible {
            display: block;
        }
        
        /* Scrollbar */
        .messages::-webkit-scrollbar {
            width: 8px;
        }
        
        .messages::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .messages::-webkit-scrollbar-thumb {
            background-color: var(--vscode-scrollbarSlider-background);
            border-radius: 4px;
        }
        
        .messages::-webkit-scrollbar-thumb:hover {
            background-color: var(--vscode-scrollbarSlider-hoverBackground);
        }
    </style>
</head>
<body>
    <div class="offline-banner" id="offlineBanner">
        ⚠️ Backend disconnected. Messages will be sent when reconnected.
    </div>
    
    <div class="header">
        <div class="header-left">
            <span class="agent-badge" id="agentBadge">
                <span>🤖</span>
                <span id="agentName">Assistant</span>
            </span>
        </div>
        <div class="status">
            <span class="status-dot" id="statusDot"></span>
            <span id="statusText">Disconnected</span>
        </div>
    </div>
    
    <div class="messages" id="messages"></div>
    
    <div class="welcome" id="welcome">
        <div class="welcome-icon">🤖</div>
        <h2>Welcome to OMNI</h2>
        <p>Start a conversation with your AI assistant. Ask questions, get help with code, or explore ideas.</p>
    </div>
    
    <div class="typing-indicator" id="typingIndicator">
        <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <span>Agent is thinking...</span>
    </div>
    
    <div class="input-container">
        <div class="input-wrapper">
            <textarea 
                id="messageInput" 
                placeholder="Type your message... (Shift+Enter for new line)"
                rows="1"
            ></textarea>
            <button class="btn" id="sendButton">
                <span>Send</span>
            </button>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const agentName = document.getElementById('agentName');
        const typingIndicator = document.getElementById('typingIndicator');
        const offlineBanner = document.getElementById('offlineBanner');
        const welcome = document.getElementById('welcome');
        
        let isConnected = false;
        let isStreaming = false;
        let streamingMessage = null;
        let streamingContent = '';
        let pendingMessages = [];
        
        // Restore state
        const previousState = vscode.getState() || {};
        if (previousState.messages) {
            previousState.messages.forEach(msg => addMessageToDOM(msg.role, msg.content, false));
        }
        
        // Auto-resize textarea
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
        });
        
        // Handle incoming messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'addMessage':
                    addMessage(message.role, message.content);
                    break;
                case 'connected':
                    setConnected(true);
                    break;
                case 'disconnected':
                    setConnected(false);
                    break;
                case 'agentChanged':
                    setAgent(message.agentId);
                    break;
                case 'streamStart':
                    startStreaming();
                    break;
                case 'streamChunk':
                    appendStreamChunk(message.content);
                    break;
                case 'streamEnd':
                    endStreaming();
                    break;
                case 'error':
                    showError(message.message);
                    break;
                case 'clearHistory':
                    clearMessages();
                    break;
            }
        });
        
        function setConnected(connected) {
            isConnected = connected;
            statusDot.classList.remove('connected', 'connecting');
            if (connected) {
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
                offlineBanner.classList.remove('visible');
                sendButton.disabled = false;
                messageInput.disabled = false;
                
                // Send pending messages
                while (pendingMessages.length > 0) {
                    const msg = pendingMessages.shift();
                    vscode.postMessage({ type: 'sendMessage', content: msg });
                }
            } else {
                statusText.textContent = 'Disconnected';
                offlineBanner.classList.add('visible');
            }
        }
        
        function setAgent(agentId) {
            const displayName = agentId.split('_').map(w => 
                w.charAt(0).toUpperCase() + w.slice(1)
            ).join(' ');
            agentName.textContent = displayName;
        }
        
        function addMessage(role, content) {
            addMessageToDOM(role, content, true);
            saveState();
            updateWelcome();
        }
        
        function addMessageToDOM(role, content, animate) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            if (!animate) div.style.animation = 'none';
            
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const roleLabel = role === 'user' ? 'You' : agentName.textContent;
            
            div.innerHTML = \`
                <div class="message-header">
                    <span>\${roleLabel}</span>
                    <span>\${time}</span>
                </div>
                <div class="message-content">\${formatMessage(content)}</div>
            \`;
            
            messagesContainer.appendChild(div);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Add copy buttons to code blocks
            div.querySelectorAll('pre').forEach(addCopyButton);
        }
        
        function formatMessage(content) {
            // Escape HTML first
            let escaped = content
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // Code blocks with language
            escaped = escaped.replace(/\\\`\\\`\\\`(\\w*)\\n([\\s\\S]*?)\\\`\\\`\\\`/g, (match, lang, code) => {
                const langLabel = lang || 'code';
                return \`<div class="code-header"><span>\${langLabel}</span></div><pre><code>\${code.trim()}</code></pre>\`;
            });
            
            // Inline code
            escaped = escaped.replace(/\\\`([^\\\`]+)\\\`/g, '<code>$1</code>');
            
            // Bold
            escaped = escaped.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
            
            // Italic
            escaped = escaped.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');
            
            // Line breaks
            escaped = escaped.replace(/\\n/g, '<br>');
            
            return escaped;
        }
        
        function addCopyButton(pre) {
            const btn = document.createElement('button');
            btn.className = 'copy-btn';
            btn.textContent = 'Copy';
            btn.onclick = async () => {
                const code = pre.querySelector('code').textContent;
                await navigator.clipboard.writeText(code);
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = 'Copy';
                    btn.classList.remove('copied');
                }, 2000);
            };
            
            const header = pre.previousElementSibling;
            if (header && header.classList.contains('code-header')) {
                header.appendChild(btn);
            }
        }
        
        function startStreaming() {
            isStreaming = true;
            streamingContent = '';
            typingIndicator.classList.add('visible');
            
            streamingMessage = document.createElement('div');
            streamingMessage.className = 'message assistant';
            
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            streamingMessage.innerHTML = \`
                <div class="message-header">
                    <span>\${agentName.textContent}</span>
                    <span>\${time}</span>
                </div>
                <div class="message-content"></div>
            \`;
            
            messagesContainer.appendChild(streamingMessage);
            updateWelcome();
        }
        
        function appendStreamChunk(content) {
            if (streamingMessage) {
                streamingContent += content;
                const contentDiv = streamingMessage.querySelector('.message-content');
                contentDiv.innerHTML = formatMessage(streamingContent);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
        
        function endStreaming() {
            isStreaming = false;
            typingIndicator.classList.remove('visible');
            
            if (streamingMessage) {
                // Add copy buttons to code blocks
                streamingMessage.querySelectorAll('pre').forEach(addCopyButton);
            }
            
            streamingMessage = null;
            streamingContent = '';
            saveState();
        }
        
        function showError(message) {
            const div = document.createElement('div');
            div.className = 'message error';
            div.innerHTML = \`
                <div class="message-header">
                    <span>Error</span>
                </div>
                <div class="message-content">⚠️ \${message}</div>
            \`;
            messagesContainer.appendChild(div);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            updateWelcome();
        }
        
        function clearMessages() {
            messagesContainer.innerHTML = '';
            vscode.setState({ messages: [] });
            updateWelcome();
        }
        
        function updateWelcome() {
            welcome.classList.toggle('hidden', messagesContainer.children.length > 0);
        }
        
        function saveState() {
            const messages = [];
            messagesContainer.querySelectorAll('.message:not(.error)').forEach(el => {
                const role = el.classList.contains('user') ? 'user' : 'assistant';
                const content = el.querySelector('.message-content')?.textContent || '';
                if (content) messages.push({ role, content });
            });
            vscode.setState({ messages });
        }
        
        function sendMessage() {
            const content = messageInput.value.trim();
            if (!content) return;
            
            // Add message immediately for UX
            addMessage('user', content);
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            if (isConnected) {
                vscode.postMessage({ type: 'sendMessage', content });
            } else {
                // Queue for later
                pendingMessages.push(content);
            }
        }
        
        sendButton.addEventListener('click', sendMessage);
        
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Initial state
        updateWelcome();
        
        // Signal that the webview is ready
        vscode.postMessage({ type: 'ready' });
    </script>
</body>
</html>`;
    }
}
exports.ChatViewProvider = ChatViewProvider;
//# sourceMappingURL=chatViewProvider.js.map