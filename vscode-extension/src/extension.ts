/**
 * OMNI AI Assistant - VS Code Extension
 * 
 * Main extension entry point.
 * Handles activation, command registration, and backend lifecycle.
 */

import * as vscode from 'vscode';
import { BackendManager } from './backend/backendManager';
import { ChatViewProvider } from './views/chatViewProvider';
import { AgentsTreeProvider } from './views/agentsTreeProvider';
import { HistoryTreeProvider } from './views/historyTreeProvider';
import { CommandHandler } from './commands/commandHandler';
import { EventBus } from './events/eventBus';
import { FileWatcher } from './watchers/fileWatcher';

let backendManager: BackendManager | undefined;
let eventBus: EventBus | undefined;
let fileWatcher: FileWatcher | undefined;

export async function activate(context: vscode.ExtensionContext) {
    console.log('OMNI AI Assistant is activating...');

    // Initialize event bus for internal communication
    eventBus = new EventBus();

    // Initialize backend manager
    backendManager = new BackendManager(context, eventBus);

    // Initialize view providers
    const chatViewProvider = new ChatViewProvider(
        context.extensionUri,
        backendManager,
        eventBus
    );

    const agentsTreeProvider = new AgentsTreeProvider(backendManager, eventBus);
    const historyTreeProvider = new HistoryTreeProvider(context, eventBus);

    // Register webview provider
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'omni.chatView',
            chatViewProvider,
            {
                webviewOptions: {
                    retainContextWhenHidden: true
                }
            }
        )
    );

    // Register tree view providers
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('omni.agentsView', agentsTreeProvider),
        vscode.window.registerTreeDataProvider('omni.historyView', historyTreeProvider)
    );

    // Initialize command handler and register commands
    const commandHandler = new CommandHandler(
        context,
        backendManager,
        chatViewProvider,
        eventBus
    );
    
    // Wire up tree providers to command handler
    commandHandler.setTreeProviders(agentsTreeProvider, historyTreeProvider);
    commandHandler.registerCommands();

    // Auto-start backend if configured
    const config = vscode.workspace.getConfiguration('omni');
    if (config.get<boolean>('backend.autoStart', true)) {
        try {
            await backendManager.start();
            vscode.window.showInformationMessage('OMNI AI Assistant is ready!');
            
            // Initialize file watcher AFTER backend is connected
            fileWatcher = new FileWatcher(backendManager, eventBus);
            context.subscriptions.push(fileWatcher);
            
        } catch (error) {
            vscode.window.showWarningMessage(
                `OMNI backend failed to start: ${error}. Some features may be unavailable.`
            );
        }
    }

    // Register commands for manual analysis
    context.subscriptions.push(
        vscode.commands.registerCommand('omni.analyzeCurrentFile', async () => {
            if (fileWatcher) {
                await fileWatcher.analyzeCurrentFile();
            }
        }),
        vscode.commands.registerCommand('omni.scanWorkspace', async () => {
            if (fileWatcher) {
                await fileWatcher.scanCurrentWorkspace();
            }
        })
    );

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
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
        statusBarItem.backgroundColor = new vscode.ThemeColor(
            'statusBarItem.warningBackground'
        );
    });

    console.log('OMNI AI Assistant activated successfully');
}

export async function deactivate() {
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
