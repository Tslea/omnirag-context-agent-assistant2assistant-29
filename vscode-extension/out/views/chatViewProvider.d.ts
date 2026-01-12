/**
 * Chat View Provider
 *
 * Webview panel for the chat interface.
 */
import * as vscode from 'vscode';
import { BackendManager } from '../backend/backendManager';
import { EventBus } from '../events/eventBus';
export declare class ChatViewProvider implements vscode.WebviewViewProvider {
    static readonly viewType = "omni.chatView";
    private view?;
    private extensionUri;
    private backendManager;
    private eventBus;
    private currentAgent;
    private messageHistory;
    constructor(extensionUri: vscode.Uri, backendManager: BackendManager, eventBus: EventBus);
    private setupEventListeners;
    resolveWebviewView(webviewView: vscode.WebviewView, _context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    private handleSendMessage;
    private addMessage;
    private clearHistory;
    private sendInitialState;
    private postMessage;
    /**
     * Add a message from external command (e.g., explain code).
     */
    sendMessage(content: string): Promise<void>;
    private getHtmlContent;
}
//# sourceMappingURL=chatViewProvider.d.ts.map