"use strict";
/**
 * Command Handler
 *
 * Registers and handles all extension commands.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommandHandler = void 0;
const vscode = __importStar(require("vscode"));
class CommandHandler {
    context;
    backendManager;
    chatViewProvider;
    eventBus;
    agentsTreeProvider;
    historyTreeProvider;
    constructor(context, backendManager, chatViewProvider, eventBus) {
        this.context = context;
        this.backendManager = backendManager;
        this.chatViewProvider = chatViewProvider;
        this.eventBus = eventBus;
    }
    /**
     * Set tree providers for commands that need them.
     */
    setTreeProviders(agentsProvider, historyProvider) {
        this.agentsTreeProvider = agentsProvider;
        this.historyTreeProvider = historyProvider;
    }
    registerCommands() {
        const commands = [
            // Core commands
            { id: 'omni.startChat', handler: () => this.startChat() },
            { id: 'omni.stopBackend', handler: () => this.stopBackend() },
            { id: 'omni.restartBackend', handler: () => this.restartBackend() },
            { id: 'omni.openSettings', handler: () => this.openSettings() },
            // Agent commands
            { id: 'omni.selectAgent', handler: (agentId) => this.selectAgent(agentId) },
            { id: 'omni.enableAgent', handler: (agentId) => this.enableAgent(agentId) },
            { id: 'omni.disableAgent', handler: (agentId) => this.disableAgent(agentId) },
            { id: 'omni.refreshAgents', handler: () => this.refreshAgents() },
            // History commands
            { id: 'omni.newSession', handler: () => this.newSession() },
            { id: 'omni.loadSession', handler: (sessionId) => this.loadSession(sessionId) },
            { id: 'omni.deleteSession', handler: (sessionId) => this.deleteSession(sessionId) },
            { id: 'omni.exportSession', handler: (sessionId) => this.exportSession(sessionId) },
            { id: 'omni.clearHistory', handler: () => this.clearHistory() },
            // Code commands
            { id: 'omni.explainCode', handler: () => this.explainCode() },
            { id: 'omni.reviewCode', handler: () => this.reviewCode() },
            { id: 'omni.generateCode', handler: () => this.generateCode() },
        ];
        for (const cmd of commands) {
            this.context.subscriptions.push(vscode.commands.registerCommand(cmd.id, cmd.handler));
        }
    }
    async startChat() {
        // Focus the chat view
        await vscode.commands.executeCommand('omni.chatView.focus');
    }
    async stopBackend() {
        try {
            await this.backendManager.stop();
            vscode.window.showInformationMessage('OMNI backend stopped');
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to stop backend: ${error}`);
        }
    }
    async restartBackend() {
        try {
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Restarting OMNI backend...',
                cancellable: false,
            }, async () => {
                await this.backendManager.restart();
            });
            vscode.window.showInformationMessage('OMNI backend restarted');
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to restart backend: ${error}`);
        }
    }
    async selectAgent(agentId) {
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
    openSettings() {
        vscode.commands.executeCommand('workbench.action.openSettings', '@ext:omni.omni-ai-assistant');
    }
    async explainCode() {
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
    async reviewCode() {
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
    async generateCode() {
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
    async enableAgent(agentId) {
        if (this.agentsTreeProvider) {
            await this.agentsTreeProvider.enableAgent(agentId);
        }
    }
    async disableAgent(agentId) {
        if (this.agentsTreeProvider) {
            await this.agentsTreeProvider.disableAgent(agentId);
        }
    }
    refreshAgents() {
        if (this.agentsTreeProvider) {
            this.agentsTreeProvider.refresh();
        }
    }
    // ==================== History Commands ====================
    newSession() {
        if (this.historyTreeProvider) {
            this.historyTreeProvider.startNewSession();
        }
    }
    async loadSession(sessionId) {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.loadSession(sessionId);
        }
    }
    async deleteSession(sessionId) {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.deleteSession(sessionId);
        }
    }
    async exportSession(sessionId) {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.exportSession(sessionId);
        }
    }
    async clearHistory() {
        if (this.historyTreeProvider) {
            await this.historyTreeProvider.clearHistory();
        }
    }
}
exports.CommandHandler = CommandHandler;
//# sourceMappingURL=commandHandler.js.map