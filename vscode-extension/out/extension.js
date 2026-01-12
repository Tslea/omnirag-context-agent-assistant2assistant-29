"use strict";
/**
 * OMNI AI Assistant - VS Code Extension
 *
 * Main extension entry point.
 * Handles activation, command registration, and backend lifecycle.
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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const backendManager_1 = require("./backend/backendManager");
const chatViewProvider_1 = require("./views/chatViewProvider");
const agentsTreeProvider_1 = require("./views/agentsTreeProvider");
const historyTreeProvider_1 = require("./views/historyTreeProvider");
const commandHandler_1 = require("./commands/commandHandler");
const eventBus_1 = require("./events/eventBus");
const fileWatcher_1 = require("./watchers/fileWatcher");
let backendManager;
let eventBus;
let fileWatcher;
async function activate(context) {
    console.log('OMNI AI Assistant is activating...');
    // Initialize event bus for internal communication
    eventBus = new eventBus_1.EventBus();
    // Initialize backend manager
    backendManager = new backendManager_1.BackendManager(context, eventBus);
    // Initialize view providers
    const chatViewProvider = new chatViewProvider_1.ChatViewProvider(context.extensionUri, backendManager, eventBus);
    const agentsTreeProvider = new agentsTreeProvider_1.AgentsTreeProvider(backendManager, eventBus);
    const historyTreeProvider = new historyTreeProvider_1.HistoryTreeProvider(context, eventBus);
    // Register webview provider
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('omni.chatView', chatViewProvider, {
        webviewOptions: {
            retainContextWhenHidden: true
        }
    }));
    // Register tree view providers
    context.subscriptions.push(vscode.window.registerTreeDataProvider('omni.agentsView', agentsTreeProvider), vscode.window.registerTreeDataProvider('omni.historyView', historyTreeProvider));
    // Initialize command handler and register commands
    const commandHandler = new commandHandler_1.CommandHandler(context, backendManager, chatViewProvider, eventBus);
    // Wire up tree providers to command handler
    commandHandler.setTreeProviders(agentsTreeProvider, historyTreeProvider);
    commandHandler.registerCommands();
    // Auto-start backend if configured
    const config = vscode.workspace.getConfiguration('omni');
    if (config.get('backend.autoStart', true)) {
        try {
            await backendManager.start();
            vscode.window.showInformationMessage('OMNI AI Assistant is ready!');
            // Initialize file watcher AFTER backend is connected
            fileWatcher = new fileWatcher_1.FileWatcher(backendManager, eventBus);
            context.subscriptions.push(fileWatcher);
        }
        catch (error) {
            vscode.window.showWarningMessage(`OMNI backend failed to start: ${error}. Some features may be unavailable.`);
        }
    }
    // Register commands for manual analysis
    context.subscriptions.push(vscode.commands.registerCommand('omni.analyzeCurrentFile', async () => {
        if (fileWatcher) {
            await fileWatcher.analyzeCurrentFile();
        }
    }), vscode.commands.registerCommand('omni.scanWorkspace', async () => {
        if (fileWatcher) {
            await fileWatcher.scanCurrentWorkspace();
        }
    }));
    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'omni.startChat';
    statusBarItem.text = '$(hubot) OMNI';
    statusBarItem.tooltip = 'OMNI AI Assistant';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // Update status bar based on backend state
    eventBus.on('backend:connected', () => {
        statusBarItem.text = '$(hubot) OMNI';
        statusBarItem.backgroundColor = undefined;
    });
    eventBus.on('backend:disconnected', () => {
        statusBarItem.text = '$(hubot) OMNI (Offline)';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    });
    console.log('OMNI AI Assistant activated successfully');
}
async function deactivate() {
    console.log('OMNI AI Assistant is deactivating...');
    if (fileWatcher) {
        fileWatcher.dispose();
    }
    if (backendManager) {
        await backendManager.stop();
    }
    if (eventBus) {
        eventBus.dispose();
    }
}
//# sourceMappingURL=extension.js.map