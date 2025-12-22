import { useEffect, useMemo, useState } from "react"
import { MCPServer, mcpServerAPI } from "@/lib/mcpConfig";
import McpConfigureModal from "@/components/ui/mcpConfigureModal";
import { useApp } from "@/context";
import { Server } from "lucide-react";
import ItemWithTrash from "@/components/ui/itemWithTrash";
import BottomButton from "./components/bottomButton";
import { Skeleton } from "antd";

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

    return <div className="left-panel">
        <div className="flex-1 overflow-y-auto space-y-2 p-4">
            <h3 className="font-title text-text-default">Mcp Servers</h3>
            <div className="flex-1 space-y-2">
                {
                    loading ? <Skeleton /> : <>
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
                                    <div className="flex flex-col justify-center">
                                        <span className="font-default text-text-default">
                                            {server.name}
                                        </span>
                                        <span className="font-title text-text-disabled">
                                            Tools:
                                        </span>
                                        <ul className="font-title text-text-disabled ml-2 space-y-1">
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
                    </>
                }
            </div>
        </div>

        {/* Footer */}
        <BottomButton 
            text={"Add Server"}
            icon={<Server className="w-4 h-4" />}
            onClick={() => {
                    setOpen(true)
                }
            }
        />

        <McpConfigureModal
            open={open}
            setOpen={setOpen}
            server={currentServer}
        />
    </div>
}

export default ServersPanel