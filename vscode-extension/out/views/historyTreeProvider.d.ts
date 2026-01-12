/**
 * History Tree View Provider
 *
 * Displays chat session history with persistence.
 * Sessions are stored locally and work offline.
 */
import * as vscode from 'vscode';
import { EventBus } from '../events/eventBus';
export declare class HistoryTreeProvider implements vscode.TreeDataProvider<HistoryTreeItem> {
    private context;
    private eventBus;
    private _onDidChangeTreeData;
    readonly onDidChangeTreeData: vscode.Event<HistoryTreeItem | undefined>;
    private sessions;
    private currentSessionId;
    private readonly storageKey;
    private readonly maxSessions;
    constructor(context: vscode.ExtensionContext, eventBus: EventBus);
    private setupEventListeners;
    private loadSessions;
    private saveSessions;
    private ensureCurrentSession;
    private createSession;
    private addMessageToCurrentSession;
    refresh(): void;
    /**
     * Start a new chat session.
     */
    startNewSession(): void;
    /**
     * Clear all history.
     */
    clearHistory(): Promise<void>;
    /**
     * Delete a specific session.
     */
    deleteSession(sessionId: string): Promise<void>;
    /**
     * Load a session (emit event to restore messages).
     */
    loadSession(sessionId: string): Promise<void>;
    /**
     * Export session to file.
     */
    exportSession(sessionId: string): Promise<void>;
    getTreeItem(element: HistoryTreeItem): vscode.TreeItem;
    getChildren(element?: HistoryTreeItem): Thenable<HistoryTreeItem[]>;
}
declare class HistoryTreeItem extends vscode.TreeItem {
    constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState);
}
export {};
//# sourceMappingURL=historyTreeProvider.d.ts.map