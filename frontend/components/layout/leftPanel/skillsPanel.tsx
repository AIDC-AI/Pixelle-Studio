import { Link, Trash2, Wrench } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Skill } from "@/types/skill";
import { api } from "@/lib/api";
import SkillConfigureModal from "@/components/ui/skillConfigureModal";
import ExpandeBox from "@/components/ui/expandeBox";
import { useApp } from "@/context";
import { mcpServerAPI } from "@/lib/mcpServerApi";
import McpServerConfigureModal from "@/components/ui/mcpServerConfigureModal";
import { MCPServer, MCPTool } from "@/types/server";

const SkillsPanel = () => {
    const { config, setConfig } = useApp()
    
    const [serverTools, setServerTools] = useState<Record<string, MCPTool[]>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [skills, setSkills] = useState<Skill[]>([])
    const [toolsConfigureOpen, setToolsConfigureOpen] = useState<boolean>(false);
    const [mcpServersConfigureOpen, setMcpServersConfigureOpen] = useState<boolean>(false);
    const [selectedIndex, setSelectedIndex] = useState<number>(-1)
    const [currentServer, setCurrentServer] = useState<MCPServer | null>(null);

    const handleGetSkills = async () => {
        setLoading(true);

        try {
            const response = await api.getSkills();
            setSkills(response)
        } catch (error) {
            console.error(`Failed to fetch skills:`, error);
        }

        setLoading(false);
    };

    const handleDeleteSkill = async (name: string) => {
        if (!name || name === '') 
            return
        try {
            const response = await api.deleteSkill(name)
            if (response) {
                handleGetSkills()
            }
        }
        catch (error) {
            console.error(`Failed to delete skill ${name}:`, error);
        }
    }

    const handleGetMcpServers = async () => {
        setLoading(true);

        for (const server of config.servers) {
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
    
    useEffect(() => {
        handleGetSkills()
    }, [])

    useEffect(() => {
        handleGetMcpServers()
    }, [config.servers])

    const servers = useMemo(() => {
        return config.servers.map(server => ({
            id: server.id,
            name: server.name,
            type: server.type,
            tools: serverTools[server.id] || []
        }))
    }, [config.servers, serverTools])

    return <div className="left-panel p-4 gap-4">
        <ExpandeBox 
            title={
                <div
                    className="flex items-center gap-2 hover:opacity-70 transition-opacity"
                >
                    <Wrench className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-800">工具</span>
                    <span className="text-xs text-gray-400">({servers.reduce((acc, s) => acc + (s.tools?.length || 0), 0)})</span>
                </div>
            }
            onAdd={() => setToolsConfigureOpen(true)}
        >
            <div className="p-4 space-y-2">
                {
                    servers?.map((server) => (
                        <div key={server.id} className="border border-gray-100 rounded-lg p-2">
                            <div className="flex items-center gap-2 mb-1">
                            <div className={`w-2 h-2 rounded-full ${
                                server.status === 'connected' ? 'bg-green-500' : 
                                server.status === 'error' ? 'bg-red-500' : 'bg-gray-400'
                            }`} />
                            <span className="text-sm font-medium text-gray-800">{server.name}</span>
                            <div className="flex-1" />
                            <button
                                onClick={() => handleTestMcpServer(server.id)}
                                className="p-1 hover:bg-gray-100 rounded transition-colors"
                                title="测试连接"
                            >
                                <Link className="w-3.5 h-3.5 text-gray-500" />
                            </button>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleDeleteServer(server.id)
                                }}
                                className="p-1 hover:bg-gray-100 rounded transition-colors"
                            >
                                <Trash2 className="w-3.5 h-3.5 text-gray-500" />
                            </button>
                            </div>
                            
                            {server.error && (
                            <p className="text-xs text-red-500 mb-1">{server.error}</p>
                            )}
                            
                            {server.tools && server.tools.length > 0 && (
                            <div className="pl-4 space-y-1">
                                {server.tools.map((tool, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-xs text-gray-600">
                                    <Check className="w-3 h-3 text-green-500" />
                                    <span>{tool.name}</span>
                                </div>
                                ))}
                            </div>
                            )}
                        </div>
                    ))
                }
            </div>
        </ExpandeBox>  
        {/* <h3 className="font-title text-gray-500">能力列表</h3>
        <div className="flex-1 space-y-2">
            {
                loading ? <Skeleton /> : <>
                    {
                        skills?.map((skill, index) => (
                            <ItemWithTrash
                                key={`${skill.name}-${index}`}
                                // selected={selectedIndex === index}
                                onItem={(e) => {
                                    e.stopPropagation()
                                    setSelectedIndex(index)
                                    setOpen(true)
                                }}
                                onTrash={() => {
                                    handleDeleteSkill(skill.name)
                                }}
                            >
                                <div className="flex flex-col">
                                    <span className="font-default text-gray-800">{skill.name}</span>
                                    <Description 
                                        description={skill.description} 
                                    />
                                </div>
                            </ItemWithTrash>
                        ))
                    }
                </>
            }
        </div> */}

        <SkillConfigureModal 
            open={toolsConfigureOpen}
            setOpen={setToolsConfigureOpen}
            setSelectedIndex={setSelectedIndex}
            skillName={skills?.[selectedIndex]?.name}
            reload={handleGetSkills}
        />

        <McpServerConfigureModal
            open={mcpServersConfigureOpen}
            setOpen={setMcpServersConfigureOpen}
            server={currentServer}
        />
    </div>
}

export default SkillsPanel