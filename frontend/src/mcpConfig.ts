export interface MCPServer {
    id: string;
    name: string;
    type: 'sse' | 'stdio' | 'http';
    config: {
        // For SSE
        url?: string;

        // For stdio
        command?: string;
        args?: string[];
        env?: Record<string, string>;

        // For HTTP
        endpoint?: string;
        headers?: Record<string, string>;
    };
    enabled: boolean;
}

export interface MCPServerConfig {
    servers: MCPServer[];
}

// Local storage key
const MCP_CONFIG_KEY = 'mcp_server_config';

export const mcpServerAPI = {
    // Load from localStorage
    loadConfig: (): MCPServerConfig => {
        const stored = localStorage.getItem(MCP_CONFIG_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
        return { servers: [] };
    },

    // Save to localStorage
    saveConfig: (config: MCPServerConfig): void => {
        localStorage.setItem(MCP_CONFIG_KEY, JSON.stringify(config));
    },

    // Add a server
    addServer: (server: Omit<MCPServer, 'id'>): MCPServer => {
        const config = mcpServerAPI.loadConfig();
        const newServer = {
            ...server,
            id: `mcp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        };
        config.servers.push(newServer);
        mcpServerAPI.saveConfig(config);
        return newServer;
    },

    // Update a server
    updateServer: (id: string, updates: Partial<MCPServer>): void => {
        const config = mcpServerAPI.loadConfig();
        const index = config.servers.findIndex(s => s.id === id);
        if (index !== -1) {
            config.servers[index] = { ...config.servers[index], ...updates };
            mcpServerAPI.saveConfig(config);
        }
    },

    // Delete a server
    deleteServer: (id: string): void => {
        const config = mcpServerAPI.loadConfig();
        config.servers = config.servers.filter(s => s.id !== id);
        mcpServerAPI.saveConfig(config);
    },

    // Get enabled servers
    getEnabledServers: (): MCPServer[] => {
        const config = mcpServerAPI.loadConfig();
        return config.servers.filter(s => s.enabled);
    }
};
