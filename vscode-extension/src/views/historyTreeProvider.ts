/**
 * History Tree View Provider
 * 
 * Displays chat session history with persistence.
 * Sessions are stored locally and work offline.
 */

import * as vscode from 'vscode';
import { EventBus, Events } from '../events/eventBus';

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

interface ChatSession {
    id: string;
    title: string;
    timestamp: string;
    messageCount: number;
    messages: ChatMessage[];
    agentId: string;
}

export class HistoryTreeProvider implements vscode.TreeDataProvider<HistoryTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<HistoryTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private sessions: ChatSession[] = [];
    private currentSessionId: string | null = null;
    private readonly storageKey = 'omni.chatSessions';
    private readonly maxSessions = 50;

    constructor(
        private context: vscode.ExtensionContext,
        private eventBus: EventBus
    ) {
        this.loadSessions();
        this.setupEventListeners();
    }

    private setupEventListeners(): void {
        // Listen for new messages to update current session
        this.eventBus.on(Events.CHAT_MESSAGE_SENT, (data) => {
            this.addMessageToCurrentSession('user', data.content);
        });

        this.eventBus.on(Events.CHAT_MESSAGE_RECEIVED, (data) => {
            this.addMessageToCurrentSession('assistant', data.content);
        });

        // Listen for agent changes to track which agent is being used
        this.eventBus.on(Events.AGENT_SELECTED, (data) => {
            if (this.currentSessionId) {
                const session = this.sessions.find(s => s.id === this.currentSessionId);
                if (session) {
                    session.agentId = data.agentId;
                    this.saveSessions();
                }
            }
        });
    }

    private loadSessions(): void {
        try {
            const saved = this.context.globalState.get<ChatSession[]>(this.storageKey, []);
            this.sessions = saved.map(s => ({
                ...s,
                messages: s.messages || [],
            }));
            
            // Ensure we have a current session for today
            this.ensureCurrentSession();
        } catch (error) {
            console.error('Failed to load chat sessions:', error);
            this.sessions = [];
        }
    }

    private saveSessions(): void {
        try {
            // Limit stored sessions
            const toSave = this.sessions.slice(0, this.maxSessions);
            this.context.globalState.update(this.storageKey, toSave);
        } catch (error) {
            console.error('Failed to save chat sessions:', error);
        }
    }

    private ensureCurrentSession(): void {
        const today = new Date().toDateString();
        let currentSession = this.sessions.find(
            s => new Date(s.timestamp).toDateString() === today
        );

        if (!currentSession) {
            currentSession = this.createSession();
        }
        
        this.currentSessionId = currentSession.id;
    }

    private createSession(title?: string): ChatSession {
        const now = new Date();
        const session: ChatSession = {
            id: `session_${now.getTime()}`,
            title: title || `Session - ${now.toLocaleDateString()}`,
            timestamp: now.toISOString(),
            messageCount: 0,
            messages: [],
            agentId: 'assistant',
        };
        
        this.sessions.unshift(session);
        this.saveSessions();
        return session;
    }

    private addMessageToCurrentSession(role: 'user' | 'assistant', content: string): void {
        this.ensureCurrentSession();
        
        const session = this.sessions.find(s => s.id === this.currentSessionId);
        if (session) {
            session.messages.push({
                role,
                content,
                timestamp: new Date().toISOString(),
            });
            session.messageCount = session.messages.length;
            
            // Update title based on first user message if default
            if (session.messages.length === 1 && role === 'user') {
                const preview = content.slice(0, 40) + (content.length > 40 ? '...' : '');
                session.title = preview;
            }
            
            this.saveSessions();
            this.refresh();
        }
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    /**
     * Start a new chat session.
     */
    startNewSession(): void {
        const session = this.createSession('New Session');
        this.currentSessionId = session.id;
        this.refresh();
        vscode.window.showInformationMessage('Started new chat session');
    }

    /**
     * Clear all history.
     */
    async clearHistory(): Promise<void> {
        const confirm = await vscode.window.showWarningMessage(
            'Are you sure you want to clear all chat history?',
            { modal: true },
            'Clear All'
        );
        
        if (confirm === 'Clear All') {
            this.sessions = [];
            this.currentSessionId = null;
            this.saveSessions();
            this.refresh();
            vscode.window.showInformationMessage('Chat history cleared');
        }
    }

    /**
     * Delete a specific session.
     */
    async deleteSession(sessionId: string): Promise<void> {
        const index = this.sessions.findIndex(s => s.id === sessionId);
        if (index !== -1) {
            this.sessions.splice(index, 1);
            
            if (this.currentSessionId === sessionId) {
                this.currentSessionId = this.sessions[0]?.id || null;
            }
            
            this.saveSessions();
            this.refresh();
        }
    }

    /**
     * Load a session (emit event to restore messages).
     */
    async loadSession(sessionId: string): Promise<void> {
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            this.currentSessionId = sessionId;
            
            // Emit event to restore messages in chat view
            this.eventBus.emit('history:session:loaded', {
                sessionId: session.id,
                messages: session.messages,
                agentId: session.agentId,
            });
            
            vscode.window.showInformationMessage(`Loaded session: ${session.title}`);
        }
    }

    /**
     * Export session to file.
     */
    async exportSession(sessionId: string): Promise<void> {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) {
            return;
        }
        
        const content = session.messages.map(m => 
            `[${m.role.toUpperCase()}] ${new Date(m.timestamp).toLocaleString()}\n${m.content}\n`
        ).join('\n---\n\n');
        
        const uri = await vscode.window.showSaveDialog({
            defaultUri: vscode.Uri.file(`${session.title.replace(/[^a-z0-9]/gi, '_')}.txt`),
            filters: {
                'Text files': ['txt'],
                'Markdown': ['md'],
            },
        });
        
        if (uri) {
            await vscode.workspace.fs.writeFile(uri, Buffer.from(content, 'utf8'));
            vscode.window.showInformationMessage(`Session exported to ${uri.fsPath}`);
        }
    }

    getTreeItem(element: HistoryTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: HistoryTreeItem): Thenable<HistoryTreeItem[]> {
        if (!element) {
            // Root level - show sessions
            if (this.sessions.length === 0) {
                return Promise.resolve([
                    new EmptyHistoryItem()
                ]);
            }
            
            return Promise.resolve(
                this.sessions.slice(0, 20).map(session => 
                    new SessionTreeItem(session, session.id === this.currentSessionId)
                )
            );
        }
        return Promise.resolve([]);
    }
}

class HistoryTreeItem extends vscode.TreeItem {
    constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState) {
        super(label, collapsibleState);
    }
}

class SessionTreeItem extends HistoryTreeItem {
    constructor(
        public readonly session: ChatSession,
        public readonly isCurrent: boolean
    ) {
        super(session.title, vscode.TreeItemCollapsibleState.None);

        this.id = session.id;
        this.description = this.formatDate(session.timestamp);
        this.tooltip = this.getTooltip();
        this.iconPath = this.getIcon();
        this.contextValue = isCurrent ? 'session-current' : 'session';

        // Click to load session
        this.command = {
            command: 'omni.loadSession',
            title: 'Load Session',
            arguments: [session.id],
        };
    }

    private formatDate(timestamp: string): string {
        const date = new Date(timestamp);
        const now = new Date();
        const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return `Today, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return date.toLocaleDateString([], { weekday: 'long' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    }

    private getTooltip(): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.appendMarkdown(`### ${this.session.title}\n\n`);
        md.appendMarkdown(`**Messages:** ${this.session.messageCount}\n\n`);
        md.appendMarkdown(`**Agent:** ${this.session.agentId}\n\n`);
        md.appendMarkdown(`**Date:** ${new Date(this.session.timestamp).toLocaleString()}\n\n`);
        
        // Show preview of last message
        if (this.session.messages.length > 0) {
            const lastMsg = this.session.messages[this.session.messages.length - 1];
            const preview = lastMsg.content.slice(0, 100) + (lastMsg.content.length > 100 ? '...' : '');
            md.appendMarkdown(`---\n*Last message:* ${preview}`);
        }
        
        return md;
    }

    private getIcon(): vscode.ThemeIcon {
        if (this.isCurrent) {
            return new vscode.ThemeIcon('comment-discussion', new vscode.ThemeColor('charts.green'));
        }
        return new vscode.ThemeIcon('history');
    }
}

class EmptyHistoryItem extends HistoryTreeItem {
    constructor() {
        super('No chat history', vscode.TreeItemCollapsibleState.None);
        this.description = 'Start a conversation';
        this.iconPath = new vscode.ThemeIcon('info');
        this.contextValue = 'empty';
    }
}
