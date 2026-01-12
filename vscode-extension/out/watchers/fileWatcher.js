"use strict";
/**
 * File Watcher
 *
 * Watches for file changes in the workspace and triggers automatic
 * security analysis when code is modified (including by Copilot).
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
exports.FileWatcher = void 0;
const vscode = __importStar(require("vscode"));
class FileWatcher {
    backendManager;
    eventBus;
    disposables = [];
    debounceTimers = new Map();
    debounceDelay = 1000; // 1 second debounce
    enabled = true;
    // Supported file extensions for analysis
    supportedExtensions = new Set([
        '.py', '.js', '.ts', '.tsx', '.jsx',
        '.java', '.cs', '.go', '.rb', '.php',
        '.c', '.cpp', '.h', '.hpp',
        '.dart', '.kt', '.kts', '.swift', // Mobile
        '.vue', '.svelte', '.scala', '.rs', // Other languages
        '.yaml', '.yml', '.json', '.xml',
        '.sh', '.bash', '.ps1',
        '.sql', '.html', '.css', '.scss'
    ]);
    // Patterns to ignore
    ignorePatterns = [
        '**/node_modules/**',
        '**/.git/**',
        '**/dist/**',
        '**/build/**',
        '**/__pycache__/**',
        '**/.venv/**',
        '**/venv/**',
        '**/*.min.js',
        '**/*.min.css',
        '**/package-lock.json',
        '**/yarn.lock'
    ];
    constructor(backendManager, eventBus) {
        this.backendManager = backendManager;
        this.eventBus = eventBus;
        this.initialize();
    }
    initialize() {
        // Watch for document saves
        this.disposables.push(vscode.workspace.onDidSaveTextDocument((document) => {
            this.onDocumentChange(document, 'modified');
        }));
        // Watch for document changes (includes Copilot modifications)
        this.disposables.push(vscode.workspace.onDidChangeTextDocument((event) => {
            // Only trigger on actual content changes
            if (event.contentChanges.length > 0) {
                this.onDocumentChangeDebounced(event.document, 'modified');
            }
        }));
        // Watch for new files
        this.disposables.push(vscode.workspace.onDidCreateFiles((event) => {
            event.files.forEach(uri => {
                vscode.workspace.openTextDocument(uri).then(doc => {
                    this.onDocumentChange(doc, 'created');
                });
            });
        }));
        // Watch for file deletions
        this.disposables.push(vscode.workspace.onDidDeleteFiles((event) => {
            event.files.forEach(uri => {
                this.eventBus.emit('file:deleted', { uri: uri.fsPath });
            });
        }));
        // Watch for workspace folder changes
        this.disposables.push(vscode.workspace.onDidChangeWorkspaceFolders((event) => {
            event.added.forEach(folder => {
                this.scanWorkspaceFolder(folder);
            });
        }));
        // Initial workspace scan
        this.performInitialScan();
        console.log('FileWatcher initialized');
    }
    /**
     * Perform initial scan of workspace when extension activates.
     */
    async performInitialScan() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return;
        }
        // Wait a bit for backend to be ready
        await new Promise(resolve => setTimeout(resolve, 2000));
        if (!this.backendManager.connected) {
            console.log('Backend not connected, skipping initial scan');
            return;
        }
        for (const folder of workspaceFolders) {
            await this.scanWorkspaceFolder(folder);
        }
    }
    /**
     * Scan an entire workspace folder.
     */
    async scanWorkspaceFolder(folder) {
        console.log(`Scanning workspace folder: ${folder.name}`);
        this.eventBus.emit('analysis:started', {
            type: 'workspace_scan',
            folder: folder.name
        });
        try {
            // Find all supported files
            const files = await this.findSupportedFiles(folder);
            // Send workspace scan request to backend
            await this.backendManager.sendMessage({
                type: 'scan_workspace',
                data: {
                    folder_path: folder.uri.fsPath,
                    folder_name: folder.name,
                    files: files.map(f => ({
                        path: f.fsPath,
                        relative_path: vscode.workspace.asRelativePath(f),
                        language: this.getLanguageFromUri(f)
                    }))
                }
            });
            this.eventBus.emit('analysis:completed', {
                type: 'workspace_scan',
                folder: folder.name,
                fileCount: files.length
            });
        }
        catch (error) {
            console.error('Workspace scan failed:', error);
            this.eventBus.emit('analysis:error', {
                type: 'workspace_scan',
                error: String(error)
            });
        }
    }
    /**
     * Find all supported files in a workspace folder.
     */
    async findSupportedFiles(folder) {
        const supportedFiles = [];
        // Build glob pattern for supported extensions
        const extensions = Array.from(this.supportedExtensions)
            .map(ext => ext.substring(1)) // Remove leading dot
            .join(',');
        const pattern = new vscode.RelativePattern(folder, `**/*.{${extensions}}`);
        // Find files excluding ignored patterns
        const files = await vscode.workspace.findFiles(pattern, `{${this.ignorePatterns.join(',')}}`);
        // No limit - analyze all files
        return files;
    }
    /**
     * Handle document change with debouncing.
     */
    onDocumentChangeDebounced(document, changeType) {
        const key = document.uri.fsPath;
        // Clear existing timer
        const existingTimer = this.debounceTimers.get(key);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }
        // Set new timer
        const timer = setTimeout(() => {
            this.onDocumentChange(document, changeType);
            this.debounceTimers.delete(key);
        }, this.debounceDelay);
        this.debounceTimers.set(key, timer);
    }
    /**
     * Handle document change event.
     */
    async onDocumentChange(document, changeType) {
        if (!this.enabled || !this.shouldAnalyze(document)) {
            return;
        }
        if (!this.backendManager.connected) {
            return;
        }
        const event = {
            uri: document.uri,
            content: document.getText(),
            language: document.languageId,
            changeType
        };
        // Emit local event
        this.eventBus.emit('file:changed', event);
        // Send to backend for analysis
        try {
            await this.backendManager.sendMessage({
                type: 'analyze_code',
                data: {
                    file_path: document.uri.fsPath,
                    relative_path: vscode.workspace.asRelativePath(document.uri),
                    content: document.getText(),
                    language: document.languageId,
                    change_type: changeType
                }
            });
        }
        catch (error) {
            console.error('Failed to send code for analysis:', error);
        }
    }
    /**
     * Check if a document should be analyzed.
     */
    shouldAnalyze(document) {
        // Skip untitled documents
        if (document.isUntitled) {
            return false;
        }
        // Skip non-file schemes
        if (document.uri.scheme !== 'file') {
            return false;
        }
        // Check extension
        const ext = this.getExtension(document.uri);
        if (!this.supportedExtensions.has(ext)) {
            return false;
        }
        // Check ignore patterns
        const relativePath = vscode.workspace.asRelativePath(document.uri);
        for (const pattern of this.ignorePatterns) {
            if (this.matchesPattern(relativePath, pattern)) {
                return false;
            }
        }
        return true;
    }
    /**
     * Get file extension from URI.
     */
    getExtension(uri) {
        const path = uri.fsPath;
        const lastDot = path.lastIndexOf('.');
        return lastDot >= 0 ? path.substring(lastDot).toLowerCase() : '';
    }
    /**
     * Get language ID from URI.
     */
    getLanguageFromUri(uri) {
        const ext = this.getExtension(uri);
        const languageMap = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescriptreact',
            '.jsx': 'javascriptreact',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.sh': 'shellscript',
            '.bash': 'shellscript',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css'
        };
        return languageMap[ext] || 'plaintext';
    }
    /**
     * Simple glob pattern matching.
     */
    matchesPattern(path, pattern) {
        // Convert glob pattern to regex
        const regexPattern = pattern
            .replace(/\*\*/g, '.*')
            .replace(/\*/g, '[^/]*')
            .replace(/\./g, '\\.');
        return new RegExp(regexPattern).test(path);
    }
    /**
     * Enable or disable file watching.
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`FileWatcher ${enabled ? 'enabled' : 'disabled'}`);
    }
    /**
     * Trigger manual analysis of the current file.
     */
    async analyzeCurrentFile() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active file to analyze');
            return;
        }
        await this.onDocumentChange(editor.document, 'modified');
        vscode.window.showInformationMessage(`Analyzing ${editor.document.fileName}...`);
    }
    /**
     * Trigger manual workspace scan.
     */
    async scanCurrentWorkspace() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showWarningMessage('No workspace folder open');
            return;
        }
        vscode.window.showInformationMessage('Starting workspace security scan...');
        for (const folder of workspaceFolders) {
            await this.scanWorkspaceFolder(folder);
        }
    }
    dispose() {
        // Clear all debounce timers
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
        // Dispose all subscriptions
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
    }
}
exports.FileWatcher = FileWatcher;
//# sourceMappingURL=fileWatcher.js.map