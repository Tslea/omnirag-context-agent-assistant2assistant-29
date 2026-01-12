"use strict";
/**
 * Agents Tree View Provider
 *
 * Displays available agents in a tree view with status and actions.
 * Works offline with default agents, syncs when backend connects.
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
exports.AgentsTreeProvider = void 0;
const vscode = __importStar(require("vscode"));
const eventBus_1 = require("../events/eventBus");
class AgentsTreeProvider {
    backendManager;
    eventBus;
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    agents = [];
    selectedAgentId = 'assistant';
    isConnected = false;
    constructor(backendManager, eventBus) {
        this.backendManager = backendManager;
        this.eventBus = eventBus;
        this.setupEventListeners();
        this.initializeDefaultAgents();
    }
    setupEventListeners() {
        // Listen for agent list updates from backend
        this.eventBus.on(eventBus_1.Events.AGENT_LIST_UPDATED, (data) => {
            if (data.agents && Array.isArray(data.agents)) {
                this.agents = data.agents.map((a) => ({
                    ...a,
                    enabled: a.enabled !== false,
                }));
                this.refresh();
            }
        });
        // Listen for agent selection
        this.eventBus.on(eventBus_1.Events.AGENT_SELECTED, (data) => {
            this.selectedAgentId = data.agentId;
            this.refresh();
        });
        // Listen for status changes
        this.eventBus.on(eventBus_1.Events.AGENT_STATUS_CHANGED, (data) => {
            if (typeof data === 'object' && data !== null && 'agentId' in data) {
                const agent = this.agents.find(a => a.id === data.agentId);
                if (agent) {
                    agent.status = data.status;
                    this.refresh();
                }
            }
        });
        // Track connection status
        this.eventBus.on(eventBus_1.Events.BACKEND_CONNECTED, () => {
            this.isConnected = true;
            this.backendManager.getAgents();
        });
        this.eventBus.on(eventBus_1.Events.BACKEND_DISCONNECTED, () => {
            this.isConnected = false;
            // Reset to default agents when disconnected
            this.initializeDefaultAgents();
            this.refresh();
        });
    }
    initializeDefaultAgents() {
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
    refresh() {
        this._onDidChangeTreeData.fire(undefined);
    }
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (!element) {
            // Root level - show agents grouped by status
            const enabledAgents = this.agents.filter(a => a.enabled);
            const disabledAgents = this.agents.filter(a => !a.enabled);
            const items = [];
            // Add enabled agents first
            enabledAgents.forEach(agent => {
                items.push(new AgentTreeItem(agent, agent.id === this.selectedAgentId, this.isConnected));
            });
            // Add disabled agents
            disabledAgents.forEach(agent => {
                items.push(new AgentTreeItem(agent, false, this.isConnected));
            });
            return Promise.resolve(items);
        }
        return Promise.resolve([]);
    }
    /**
     * Enable an agent.
     */
    async enableAgent(agentId) {
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
    async disableAgent(agentId) {
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
    getEnabledAgents() {
        return this.agents.filter(a => a.enabled);
    }
}
exports.AgentsTreeProvider = AgentsTreeProvider;
class AgentTreeItem extends vscode.TreeItem {
    agent;
    isSelected;
    isConnected;
    constructor(agent, isSelected, isConnected) {
        super(agent.name, vscode.TreeItemCollapsibleState.None);
        this.agent = agent;
        this.isSelected = isSelected;
        this.isConnected = isConnected;
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
    getStatusDescription() {
        if (!this.agent.enabled) {
            return 'disabled';
        }
        if (this.isSelected) {
            return '● active';
        }
        return this.agent.status;
    }
    getTooltip() {
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
    getIcon() {
        if (!this.agent.enabled) {
            return new vscode.ThemeIcon('circle-slash', new vscode.ThemeColor('disabledForeground'));
        }
        if (this.isSelected) {
            return new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
        }
        const statusIcons = {
            'idle': { icon: 'circle-outline' },
            'thinking': { icon: 'loading~spin', color: 'charts.yellow' },
            'executing': { icon: 'run', color: 'charts.blue' },
            'error': { icon: 'error', color: 'charts.red' },
            'stopped': { icon: 'stop', color: 'disabledForeground' },
        };
        const config = statusIcons[this.agent.status] || statusIcons['idle'];
        return new vscode.ThemeIcon(config.icon, config.color ? new vscode.ThemeColor(config.color) : undefined);
    }
    getContextValue() {
        const parts = ['agent'];
        if (this.agent.enabled) {
            parts.push('enabled');
        }
        else {
            parts.push('disabled');
        }
        if (this.isSelected) {
            parts.push('selected');
        }
        return parts.join('-');
    }
}
//# sourceMappingURL=agentsTreeProvider.js.map