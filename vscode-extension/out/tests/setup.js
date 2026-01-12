"use strict";
/**
 * Jest Test Setup
 *
 * This file runs before each test file and sets up:
 * - VS Code API mocks (since vscode module isn't available in tests)
 * - Global test utilities
 * - Environment configuration
 *
 * Run tests with: npm test
 */
// Mock the VS Code API since it's not available outside the extension host
jest.mock('vscode', () => ({
    // Window API
    window: {
        showInformationMessage: jest.fn(),
        showErrorMessage: jest.fn(),
        showWarningMessage: jest.fn(),
        createOutputChannel: jest.fn(() => ({
            appendLine: jest.fn(),
            append: jest.fn(),
            clear: jest.fn(),
            show: jest.fn(),
            hide: jest.fn(),
            dispose: jest.fn(),
        })),
        createWebviewPanel: jest.fn(),
        registerWebviewViewProvider: jest.fn(),
        registerTreeDataProvider: jest.fn(),
        showQuickPick: jest.fn(),
        showInputBox: jest.fn(),
        withProgress: jest.fn(),
        createStatusBarItem: jest.fn(() => ({
            show: jest.fn(),
            hide: jest.fn(),
            dispose: jest.fn(),
            text: '',
            tooltip: '',
            command: undefined,
        })),
    },
    // Workspace API
    workspace: {
        getConfiguration: jest.fn(() => ({
            get: jest.fn(),
            update: jest.fn(),
            has: jest.fn(),
            inspect: jest.fn(),
        })),
        workspaceFolders: [],
        onDidChangeConfiguration: jest.fn(() => ({ dispose: jest.fn() })),
        fs: {
            readFile: jest.fn(),
            writeFile: jest.fn(),
            stat: jest.fn(),
        },
    },
    // Commands API
    commands: {
        registerCommand: jest.fn(() => ({ dispose: jest.fn() })),
        executeCommand: jest.fn(),
        getCommands: jest.fn(),
    },
    // Extension context
    ExtensionContext: jest.fn(),
    // URI utilities
    Uri: {
        file: jest.fn((path) => ({ fsPath: path, path, scheme: 'file' })),
        parse: jest.fn((uri) => ({ fsPath: uri, path: uri, scheme: 'file' })),
        joinPath: jest.fn(),
    },
    // Event emitters
    EventEmitter: jest.fn().mockImplementation(() => ({
        event: jest.fn(),
        fire: jest.fn(),
        dispose: jest.fn(),
    })),
    // Tree view
    TreeItem: jest.fn(),
    TreeItemCollapsibleState: {
        None: 0,
        Collapsed: 1,
        Expanded: 2,
    },
    // Webview
    ViewColumn: {
        One: 1,
        Two: 2,
        Three: 3,
    },
    // Status bar
    StatusBarAlignment: {
        Left: 1,
        Right: 2,
    },
    // Progress
    ProgressLocation: {
        Notification: 15,
        SourceControl: 1,
        Window: 10,
    },
    // Disposable
    Disposable: {
        from: jest.fn((...disposables) => ({
            dispose: () => disposables.forEach(d => d.dispose?.()),
        })),
    },
}), { virtual: true });
// Global test timeout
jest.setTimeout(10000);
// Clean up after all tests
afterAll(() => {
    jest.restoreAllMocks();
});
//# sourceMappingURL=setup.js.map