/**
 * File Watcher
 *
 * Watches for file changes in the workspace and triggers automatic
 * security analysis when code is modified (including by Copilot).
 */
import * as vscode from 'vscode';
import { EventBus } from '../events/eventBus';
import { BackendManager } from '../backend/backendManager';
export interface FileChangeEvent {
    uri: vscode.Uri;
    content: string;
    language: string;
    changeType: 'created' | 'modified' | 'deleted';
}
export declare class FileWatcher implements vscode.Disposable {
    private backendManager;
    private eventBus;
    private disposables;
    private debounceTimers;
    private debounceDelay;
    private enabled;
    private supportedExtensions;
    private ignorePatterns;
    constructor(backendManager: BackendManager, eventBus: EventBus);
    private initialize;
    /**
     * Perform initial scan of workspace when extension activates.
     */
    private performInitialScan;
    /**
     * Scan an entire workspace folder.
     */
    scanWorkspaceFolder(folder: vscode.WorkspaceFolder): Promise<void>;
    /**
     * Find all supported files in a workspace folder.
     */
    private findSupportedFiles;
    /**
     * Handle document change with debouncing.
     */
    private onDocumentChangeDebounced;
    /**
     * Handle document change event.
     */
    private onDocumentChange;
    /**
     * Check if a document should be analyzed.
     */
    private shouldAnalyze;
    /**
     * Get file extension from URI.
     */
    private getExtension;
    /**
     * Get language ID from URI.
     */
    private getLanguageFromUri;
    /**
     * Simple glob pattern matching.
     */
    private matchesPattern;
    /**
     * Enable or disable file watching.
     */
    setEnabled(enabled: boolean): void;
    /**
     * Trigger manual analysis of the current file.
     */
    analyzeCurrentFile(): Promise<void>;
    /**
     * Trigger manual workspace scan.
     */
    scanCurrentWorkspace(): Promise<void>;
    dispose(): void;
}
//# sourceMappingURL=fileWatcher.d.ts.map