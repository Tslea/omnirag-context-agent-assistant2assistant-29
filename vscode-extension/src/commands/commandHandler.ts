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
import { EventBus, Events } from '../events/eventBus';

export class CommandHandler {
    private agentsTreeProvider?: AgentsTreeProvider;
    private historyTreeProvider?: HistoryTreeProvider;

    constructor(
        private context: vscode.ExtensionContext,
        private backendManager: BackendManager,
        private chatViewProvider: ChatViewProvider,
        private eventBus: EventBus
    ) {}

    /**
     * Set tree providers for commands that need them.
     */
    setTreeProviders(
        agentsProvider: AgentsTreeProvider,
        historyProvider: HistoryTreeProvider
    ): void {
        this.agentsTreeProvider = agentsProvider;
        this.historyTreeProvider = historyProvider;
    }

    registerCommands(): void {
        const commands = [
            // Core commands
            { id: 'omni.startChat', handler: () => this.startChat() },
            { id: 'omni.stopBackend', handler: () => this.stopBackend() },
            { id: 'omni.restartBackend', handler: () => this.restartBackend() },
            { id: 'omni.openSettings', handler: () => this.openSettings() },
            
            // Agent commands
            { id: 'omni.selectAgent', handler: (agentId?: string) => this.selectAgent(agentId) },
            { id: 'omni.enableAgent', handler: (agentId: string) => this.enableAgent(agentId) },
            { id: 'omni.disableAgent', handler: (agentId: string) => this.disableAgent(agentId) },
            { id: 'omni.refreshAgents', handler: () => this.refreshAgents() },
            
            // History commands
            { id: 'omni.newSession', handler: () => this.newSession() },
            { id: 'omni.loadSession', handler: (sessionId: string) => this.loadSession(sessionId) },
            { id: 'omni.deleteSession', handler: (sessionId: string) => this.deleteSession(sessionId) },
            { id: 'omni.exportSession', handler: (sessionId: string) => this.exportSession(sessionId) },
            { id: 'omni.clearHistory', handler: () => this.clearHistory() },
            
            // Code commands
            { id: 'omni.explainCode', handler: () => this.explainCode() },
            { id: 'omni.reviewCode', handler: () => this.reviewCode() },
            { id: 'omni.generateCode', handler: () => this.generateCode() },
        ];

        for (const cmd of commands) {
            this.context.subscriptions.push(
                vscode.commands.registerCommand(cmd.id, cmd.handler)
            );
        }
    }

    private async startChat(): Promise<void> {
        // Focus the chat view
        await vscode.commands.executeCommand('omni.chatView.focus');
    }

    private async stopBackend(): Promise<void> {
        try {
            await this.backendManager.stop();
            vscode.window.showInformationMessage('OMNI backend stopped');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to stop backend: ${error}`);
        }
    }

    private async restartBackend(): Promise<void> {
        try {
            vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: 'Restarting OMNI backend...',
                    cancellable: false,
                },
                async () => {
                    await this.backendManager.restart();
                }
            );
            vscode.window.showInformationMessage('OMNI backend restarted');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to restart backend: ${error}`);
        }
    }

    private async selectAgent(agentId?: string): Promise<void> {
        if (agentId) {
            await this.backendManager.selectAgent(agentId);
            return;
        }

        // Show quick pick if no agent ID provided
        const agents = [
            { label: 'Assistant', description: 'General-purpose AI assistant', id: 'assistant' },
            { label: 'Code Agent', description: 'Specialized for coding tasks', id: 'code_agent' },
            { label: 'Planner', description: 'Plans complex tasks', id: 'planner' },
        ];

        const selected = await vscode.window.showQuickPick(agents, {
            placeHolder: 'Select an agent',
            title: 'OMNI - Select Agent',
        });

        if (selected) {
            await this.backendManager.selectAgent(selected.id);
            vscode.window.showInformationMessage(`Selected agent: ${selected.label}`);
        }
    }

    private openSettings(): void {
        vscode.commands.executeCommand(
            'workbench.action.openSettings',
            '@ext:omni.omni-ai-assistant'
        );
    }

    private async explainCode(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);

        if (!selectedText) {
            vscode.window.showWarningMessage('No code selected');
            return;
        }

        const language = editor.document.languageId;
        const prompt = `Please explain the following ${language} code:\n\n\`\`\`${language}\n${selectedText}\n\`\`\``;

        // Focus chat view and send message
        await vscode.commands.executeCommand('omni.chatView.focus');
        await this.chatViewProvider.sendMessage(prompt);
    }

    private async reviewCode(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);

        if (!selectedText) {
            vscode.window.showWarningMessage('No code selected');
            return;
        }

        const language = editor.document.languageId;
        const prompt = `Please review the following ${language} code for bugs, security issues, and improvements:\n\n\`\`\`${language}\n${selectedText}\n\`\`\``;

        await vscode.commands.executeCommand('omni.chatView.focus');
        await this.chatViewProvider.sendMessage(prompt);
    }

    private async generateCode(): Promise<void> {
        const description = await vscode.window.showInputBox({
            prompt: 'Describe what code you want to generate',
            placeHolder: 'e.g., A function that sorts a list of objects by date',
        });

        if (!description) {
            return;
        }

        // Get current language context
        const editor = vscode.window.activeTextEditor;
        const language = editor?.document.languageId || 'python';

        const prompt = `Generate ${language} code for the following:\n\n${description}`;

        await vscode.commands.executeCommand('omni.chatView.focus');
        await this.chatViewProvider.sendMessage(prompt);
    }

    // ==================== Agent Commands ====================

    private async enableAgent(agentId: string): Promise<void> {
        if (this.agentsTreeProvider) {
            await this.agentsTreeProvider.enableAgent(agentId);
        }
    }

    private async disableAgent(agentId: string): Promise<void> {
        if (this.agentsTreeProvider) {
            await this.agentsTreeProvider.disableAgent(agentId);
        }
    }

    private refreshAgents(): void {
        if (this.agentsTreeProvider) {
            this.agentsTreeProvider.refresh();
        }
    }

    // ==================== History Commands ====================

    private newSession(): void {
        if (this.historyTreeProvider) {
            this.historyTreeProvider.startNewSession();
        }
    }

    private async loadSession(sessionId: string): Promise<void> {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.loadSession(sessionId);
        }
    }

    private async deleteSession(sessionId: string): Promise<void> {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.deleteSession(sessionId);
        }
    }

    private async exportSession(sessionId: string): Promise<void> {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.exportSession(sessionId);
        }
    }

    private async clearHistory(): Promise<void> {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.clearHistory();
        }
    }
}
