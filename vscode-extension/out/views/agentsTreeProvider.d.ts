/**
 * Agents Tree View Provider
 *
 * Displays available agents in a tree view with status and actions.
 * Works offline with default agents, syncs when backend connects.
 */
import * as vscode from 'vscode';
import { BackendManager } from '../backend/backendManager';
import { EventBus } from '../events/eventBus';
interface AgentInfo {
    id: string;
    name: string;
    description: string;
    status: 'idle' | 'thinking' | 'executing' | 'error' | 'stopped' | 'disabled';
    capabilities: string[];
    enabled: boolean;
}
export declare class AgentsTreeProvider implements vscode.TreeDataProvider<AgentTreeItem> {
    private backendManager;
    private eventBus;
    private _onDidChangeTreeData;
    readonly onDidChangeTreeData: vscode.Event<AgentTreeItem | undefined>;
    private agents;
    private selectedAgentId;
    private isConnected;
    constructor(backendManager: BackendManager, eventBus: EventBus);
    private setupEventListeners;
    private initializeDefaultAgents;
    refresh(): void;
    getTreeItem(element: AgentTreeItem): vscode.TreeItem;
    getChildren(element?: AgentTreeItem): Thenable<AgentTreeItem[]>;
    /**
     * Enable an agent.
     */
    enableAgent(agentId: string): Promise<void>;
    /**
     * Disable an agent.
     */
    disableAgent(agentId: string): Promise<void>;
    /**
     * Get available (enabled) agents.
     */
    getEnabledAgents(): AgentInfo[];
}
declare class AgentTreeItem extends vscode.TreeItem {
    readonly agent: AgentInfo;
    readonly isSelected: boolean;
    private readonly isConnected;
    constructor(agent: AgentInfo, isSelected: boolean, isConnected: boolean);
    private getStatusDescription;
    private getTooltip;
    private getIcon;
    private getContextValue;
}
export {};
//# sourceMappingURL=agentsTreeProvider.d.ts.map