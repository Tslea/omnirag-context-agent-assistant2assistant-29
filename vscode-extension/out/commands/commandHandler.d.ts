/**
 * Command Handler
 *
 * Registers and handles all extension commands.
 */
import * as vscode from 'vscode';
import { BackendManager } from '../backend/backendManager';
import { ChatViewProvider } from '../views/chatViewProvider';
import { AgentsTreeProvider } from '../views/agentsTreeProvider';
import { HistoryTreeProvider } from '../views/historyTreeProvider';
import { EventBus } from '../events/eventBus';
export declare class CommandHandler {
    private context;
    private backendManager;
    private chatViewProvider;
    private eventBus;
    private agentsTreeProvider?;
    private historyTreeProvider?;
    constructor(context: vscode.ExtensionContext, backendManager: BackendManager, chatViewProvider: ChatViewProvider, eventBus: EventBus);
    /**
     * Set tree providers for commands that need them.
     */
    setTreeProviders(agentsProvider: AgentsTreeProvider, historyProvider: HistoryTreeProvider): void;
    registerCommands(): void;
    private startChat;
    private stopBackend;
    private restartBackend;
    private selectAgent;
    private openSettings;
    private explainCode;
    private reviewCode;
    private generateCode;
    private enableAgent;
    private disableAgent;
    private refreshAgents;
    private newSession;
    private loadSession;
    private deleteSession;
    private exportSession;
    private clearHistory;
}
//# sourceMappingURL=commandHandler.d.ts.map