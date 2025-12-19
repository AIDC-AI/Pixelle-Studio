import { useEffect, useMemo, useState } from "react"
import { MCPServer, mcpServerAPI } from "@/lib/mcpConfig";
import McpConfigureModal from "@/components/ui/mcpConfigureModal";
import { useApp } from "@/context";
import { Server } from "lucide-react";
import ItemWithTrash from "@/components/ui/itemWithTrash";

interface Tool {
    name: string;
    description: string;
}

const ServersPanel = () => {
    const { config, setConfig } = useApp()

    const [serverTools, setServerTools] = useState<Record<string, Tool[]>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [open, setOpen] = useState<boolean>(false);
    const [currentServer, setCurrentServer] = useState<MCPServer | null>(null);

    const fetchServerTools = async () => {
        setLoading(true);

        for (const server of config.servers) {
            if (!server.enabled) continue;

            try {
                const response = await fetch('http://localhost:8001/api/tools', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        servers: [server]
                    })
                });

                if (response.ok) {
                    const tools = await response.json();
                    setServerTools(prev => ({ ...prev, [server.id]: tools }));
                }
            } catch (error) {
                console.error(`Failed to fetch tools for ${server.name}:`, error);
            }
        }

        setLoading(false);
    };

    const handleDeleteServer = (id: string) => {
        mcpServerAPI.deleteServer(id);
        setConfig({ servers: config.servers.filter(s => s.id !== id) });
    };

    const servers = useMemo(() => {
        return config.servers.map(server => ({
            id: server.id,
            name: server.name,
            type: server.type,
            tools: serverTools[server.id] || []
        }))
    }, [config.servers, serverTools])

    useEffect(() => {
        fetchServerTools()
    }, [config.servers])

    return <div className="p-4 flex flex-col h-full">
        <h3 className="text-xs font-medium text-gray-500 mb-3 px-2">Mcp Servers</h3>
        <div className="flex-1 overflow-y-auto">
            {
                servers?.map((server) => (
                    <ItemWithTrash
                        key={server.id}
                        onItem={() => {
                            setCurrentServer(config.servers.find(s => s.id === server.id) || null)
                            setOpen(true)
                        }}
                        onTrash={() => {
                            handleDeleteServer(server.id)
                        }}
                    >
                        <div className="flex flex-col justify-center gap-1">
                            <span className="item-title">
                                {server.name}
                            </span>
                            <span className="item-subtitle">
                                Tools:
                            </span>
                            <ul className="text-xs text-[#666] ml-2 space-y-1">
                                {server?.tools?.map((tool, idx) => (
                                    <li key={idx}>
                                        <span>{tool.name}-</span>
                                        {tool.description && (
                                            <span>{tool.description}</span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </ItemWithTrash>
                ))
            }
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
            <button 
                className="w-full flex items-center gap-2 px-4 py-2.5 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                onClick={() => {
                    setOpen(true)
                }}
            >
                <Server className="w-4 h-4" />
                <span className="text-sm">Add Server</span>
            </button>
        </div>

        <McpConfigureModal
            open={open}
            setOpen={setOpen}
            server={currentServer}
        />
    </div>
}

export default ServersPanel