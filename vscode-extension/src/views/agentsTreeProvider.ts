/**
 * Agents Tree View Provider
 * 
 * Displays available agents in a tree view with status and actions.
 * Works offline with default agents, syncs when backend connects.
 */

import * as vscode from 'vscode';
import { BackendManager } from '../backend/backendManager';
import { EventBus, Events } from '../events/eventBus';

interface AgentInfo {
    id: string;
    name: string;
    description: string;
    status: 'idle' | 'thinking' | 'executing' | 'error' | 'stopped' | 'disabled';
    capabilities: string[];
    enabled: boolean;
}

export class AgentsTreeProvider implements vscode.TreeDataProvider<AgentTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<AgentTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private agents: AgentInfo[] = [];
    private selectedAgentId: string = 'assistant';
    private isConnected: boolean = false;

    constructor(
        private backendManager: BackendManager,
        private eventBus: EventBus
    ) {
        this.setupEventListeners();
        this.initializeDefaultAgents();
    }

    private setupEventListeners(): void {
        // Listen for agent list updates from backend
        this.eventBus.on(Events.AGENT_LIST_UPDATED, (data) => {
            if (data.agents && Array.isArray(data.agents)) {
                this.agents = data.agents.map((a: any) => ({
                    ...a,
                    enabled: a.enabled !== false,
                }));
                this.refresh();
            }
        });

        // Listen for agent selection
        this.eventBus.on(Events.AGENT_SELECTED, (data) => {
            this.selectedAgentId = data.agentId;
            this.refresh();
        });

        // Listen for status changes
        this.eventBus.on(Events.AGENT_STATUS_CHANGED, (data) => {
            if (typeof data === 'object' && data !== null && 'agentId' in data) {
                const agent = this.agents.find(a => a.id === data.agentId);
                if (agent) {
                    agent.status = data.status;
                    this.refresh();
                }
            }
        });

        // Track connection status
        this.eventBus.on(Events.BACKEND_CONNECTED, () => {
            this.isConnected = true;
            this.backendManager.getAgents();
        });

        this.eventBus.on(Events.BACKEND_DISCONNECTED, () => {
            this.isConnected = false;
            // Reset to default agents when disconnected
            this.initializeDefaultAgents();
            this.refresh();
        });
    }

    private initializeDefaultAgents(): void {
        // Default agents available even when offline
        this.agents = [
            {
                id: 'assistant',
                name: 'Assistant',
                description: 'General-purpose AI assistant for conversation and help',
                status: 'idle',
                capabilities: ['conversation', 'tool_use', 'reasoning'],
                enabled: true,
            },
            {
                id: 'code_agent',
                name: 'Code Agent',
                description: 'Specialized for code generation, review, and debugging',
                status: 'idle',
                capabilities: ['code_generation', 'code_review', 'debugging'],
                enabled: true,
            },
            {
                id: 'planner',
                name: 'Planner',
                description: 'Decomposes complex tasks into actionable steps',
                status: 'idle',
                capabilities: ['task_decomposition', 'workflow_planning', 'multi_step'],
                enabled: true,
            },
        ];
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: AgentTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AgentTreeItem): Thenable<AgentTreeItem[]> {
        if (!element) {
            // Root level - show agents grouped by status
            const enabledAgents = this.agents.filter(a => a.enabled);
            const disabledAgents = this.agents.filter(a => !a.enabled);
            
            const items: AgentTreeItem[] = [];
            
            // Add enabled agents first
            enabledAgents.forEach(agent => {
                items.push(new AgentTreeItem(
                    agent,
                    agent.id === this.selectedAgentId,
                    this.isConnected
                ));
            });
            
            // Add disabled agents
            disabledAgents.forEach(agent => {
                items.push(new AgentTreeItem(
                    agent,
                    false,
                    this.isConnected
                ));
            });
            
            return Promise.resolve(items);
        }
        return Promise.resolve([]);
    }

    /**
     * Enable an agent.
     */
    async enableAgent(agentId: string): Promise<void> {
        const agent = this.agents.find(a => a.id === agentId);
        if (agent) {
            agent.enabled = true;
            agent.status = 'idle';
            if (this.isConnected) {
                await this.backendManager.enableAgent(agentId);
            }
            this.refresh();
        }
    }

    /**
     * Disable an agent.
     */
    async disableAgent(agentId: string): Promise<void> {
        const agent = this.agents.find(a => a.id === agentId);
        if (agent) {
            // Don't disable if it's the currently selected agent
            if (agent.id === this.selectedAgentId) {
                vscode.window.showWarningMessage('Cannot disable the currently selected agent.');
                return;
            }
            agent.enabled = false;
            agent.status = 'disabled';
            if (this.isConnected) {
                await this.backendManager.disableAgent(agentId);
            }
            this.refresh();
        }
    }

    /**
     * Get available (enabled) agents.
     */
    getEnabledAgents(): AgentInfo[] {
        return this.agents.filter(a => a.enabled);
    }
}

class AgentTreeItem extends vscode.TreeItem {
    constructor(
        public readonly agent: AgentInfo,
        public readonly isSelected: boolean,
        private readonly isConnected: boolean
    ) {
        super(agent.name, vscode.TreeItemCollapsibleState.None);

        this.id = agent.id;
        this.description = this.getStatusDescription();
        this.tooltip = this.getTooltip();
        this.iconPath = this.getIcon();
        this.contextValue = this.getContextValue();

        // Set command to select this agent (only if enabled)
        if (agent.enabled) {
            this.command = {
                command: 'omni.selectAgent',
                title: 'Select Agent',
                arguments: [agent.id],
            };
        }
    }

    private getStatusDescription(): string {
        if (!this.agent.enabled) {
            return 'disabled';
        }
        if (this.isSelected) {
            return '● active';
        }
        return this.agent.status;
    }

    private getTooltip(): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.appendMarkdown(`### ${this.agent.name}\n\n`);
        md.appendMarkdown(`${this.agent.description}\n\n`);
        md.appendMarkdown(`**Status:** ${this.agent.enabled ? this.agent.status : 'disabled'}\n\n`);
        md.appendMarkdown(`**Capabilities:**\n`);
        this.agent.capabilities.forEach(cap => {
            md.appendMarkdown(`- \`${cap}\`\n`);
        });
        if (!this.isConnected) {
            md.appendMarkdown(`\n---\n*Backend offline - using cached data*`);
        }
        return md;
    }

    private getIcon(): vscode.ThemeIcon {
        if (!this.agent.enabled) {
            return new vscode.ThemeIcon('circle-slash', new vscode.ThemeColor('disabledForeground'));
        }
        
        if (this.isSelected) {
            return new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
        }
        
        const statusIcons: Record<string, { icon: string; color?: string }> = {
            'idle': { icon: 'circle-outline' },
            'thinking': { icon: 'loading~spin', color: 'charts.yellow' },
            'executing': { icon: 'run', color: 'charts.blue' },
            'error': { icon: 'error', color: 'charts.red' },
            'stopped': { icon: 'stop', color: 'disabledForeground' },
        };
        
        const config = statusIcons[this.agent.status] || statusIcons['idle'];
        return new vscode.ThemeIcon(
            config.icon,
            config.color ? new vscode.ThemeColor(config.color) : undefined
        );
    }

    private getContextValue(): string {
        const parts = ['agent'];
        if (this.agent.enabled) {
            parts.push('enabled');
        } else {
            parts.push('disabled');
        }
        if (this.isSelected) {
            parts.push('selected');
        }
        return parts.join('-');
    }
}
