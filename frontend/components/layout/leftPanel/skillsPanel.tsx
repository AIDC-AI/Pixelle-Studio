import { Book, Trash2, Wrench } from "lucide-react"
import { useEffect, useState } from "react"
import { SkillMeta } from "@/types/skill";
import ExpandeBox from "@/components/ui/expandeBox";
import { ToastType, useApp } from "@/context";
import { mcpServerAPI } from "@/lib/mcpServerApi";
import ToolConfigureModal from "@/components/ui/toolConfigureModal";
import { MCPServer, MCPTool } from "@/types/server";
import ServerCard from "@/components/ui/serverCard";
import { skillAPI } from "@/lib/skillApi";
import Description from "@/components/ui/desctiption";
import { Skeleton } from "@/components/ui/skeleton";
import SkillConfigureModal from "@/components/ui/skillConfigureModal";

const SkillsPanel = () => {
    const { 
        user, 
        // setSkillEditored, 
        // setCurrentSkillName,
        // mcpTools, 
        // setMcpTools,
        // isChangeSkill,
        // setIsChangeSkill,
        showToast
    } = useApp()

    const [loading, setLoading] = useState<boolean>(false);

    const [mcpServers, setMcpServers] = useState<MCPServer[]>([])
    const [mcpTools, setMcpTools] = useState<MCPTool[] | null>(null)
    const [skillConfigureOpen, setSkillConfigureOpen] = useState<boolean>(false)
    const [toolConfigureOpen, setToolConfigureOpen] = useState<boolean>(false)
    const [skills, setSkills] = useState<SkillMeta[]>([])

    const [selectedSkillName, setSelectedSkillName] = useState<string | null>(null)
    const [selectedMcpServerIndex, setSelectedMcpServerIndex] = useState<number>(-1)

    const handleShowSkillEditor = (name: string | null) => {
        setSelectedSkillName(name)
        setSkillConfigureOpen(true)
    }

    const handleCloseSkillEditor = (isSuccess: boolean) => {
        setSelectedSkillName(null)
        setSkillConfigureOpen(false)
        if (isSuccess) 
            handleGetSkills()
    }

    const handleGetSkills = async () => {
        setLoading(true);

        try {
            const response = await skillAPI.getSkills(user?.uid);
            setSkills(response)
        } catch (error) {
            console.error(`Failed to fetch skills:`, error);
        }

        setLoading(false);
    };

    const handleDeleteSkill = async (name: string) => {
        setLoading(true);

        try {
            await skillAPI.deleteSkill(name, user?.uid);
            setSkills(prev => prev.filter((skill) => skill.name !== name))
            // setSkillEditored(false)
            // setCurrentSkillName(null)
            showToast(ToastType.SUCCESS, 'Deletion successful!')
        } catch (error) {
            console.error(`Failed to fetch skills:`, error);
            showToast(ToastType.ERROR, (error as Error).message || 'Delete failed!')
        }

        setLoading(false);
    }

    const handleGetMcpServers = async () => {
        setLoading(true);

        try {
            const res = await mcpServerAPI.getServers(true); // Get data including status and tools
            if (!!res) {
                setMcpServers(res);
            }
        } catch (error) {
            console.error('Failed to fetch MCP servers:', error);
            showToast(ToastType.ERROR, (error as Error).message || 'Failed to fetch server list!');
        }

        setLoading(false);
    };

    const handleDeleteMcpServer = async (id: string) => {
        try {
            await mcpServerAPI.deleteServer(id);
            setMcpServers(prev => [...prev.filter((server) => server.id !== id)])
            showToast(ToastType.SUCCESS, 'Deleted successfully!')
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error).message || 'Delete failed!')
        }
    };

    const handleRefreshServer = async (serverId: string) => {
        // Mark server as checking status
        setMcpServers(prev => prev.map(s => 
            s.id === serverId ? { ...s, status: 'checking' as const } : s
        ));

        try {
            const status = await mcpServerAPI.checkServerStatus(serverId);
            // Update server status and tools
            setMcpServers(prev => prev.map(s => 
                s.id === serverId ? {
                    ...s,
                    status: status.status,
                    message: status.message,
                    response_time: status.response_time,
                    tools: status.tools
                } : s
            ));
        } catch (error) {
            console.error('Failed to refresh server status:', error);
            setMcpServers(prev => prev.map(s => 
                s.id === serverId ? {
                    ...s,
                    status: 'error' as const,
                    message: (error as Error).message || 'Failed to check status'
                } : s
            ));
        }
    };
    
    useEffect(() => {
        handleGetSkills()
        handleGetMcpServers()
    }, [])

    // useEffect(() => {
    //     if (isChangeSkill) {
    //         handleGetSkills()
    //         setIsChangeSkill(false)
    //     }
    // }, [isChangeSkill])

    // Total tool count
    useEffect(() => {
        const list = mcpServers.reduce<MCPTool[]>((total, server) => {
            if (server?.tools && Array.isArray(server.tools)) {
                const toolsWithServerName = server.tools.map(tool => ({
                    ...tool,
                    server_name: server.name
                }));
                return [...total, ...toolsWithServerName];
            }
            return total;
        }, []);
        setMcpTools(list)
    }, [mcpServers])

    return <div style={{ display: 'flex', flexDirection: 'column', flex: '1 1 0%', minHeight: 0, overflowY: 'auto', padding: 16, gap: 16 }}>
        {
            loading ? <Skeleton active /> : <>
                <ExpandeBox 
                    title={
                        <div
                            className="flex items-center gap-2 hover:opacity-70 transition-opacity"
                        >
                            <Book className="w-4 h-4 text-gray-600" />
                            <span className="text-sm font-medium text-gray-800">Skills</span>
                            <span className="text-xs text-gray-400">({skills?.length || 0})</span>
                        </div>
                    }
                    hoverContent="New Skill"
                    onAdd={() => {
                        handleShowSkillEditor(null)
                    }}
                >
                    <div className="p-4 space-y-2">
                        {
                            skills?.map((skill, index) => <div
                                key={`${skill.name}-${index}`}
                                onClick={() => {
                                    handleShowSkillEditor(skill.name)
                                }}
                                className="group flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                            >
                                <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <p className="text-sm text-gray-800 truncate">{skill.name}</p>
                                </div>
                                <Description
                                    lineCount={1}
                                    description={skill.description}
                                />
                                {/* <p className="text-xs text-gray-500 truncate">{skill.description}</p> */}
                                </div>
                                {
                                    !skill.is_default && <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            handleDeleteSkill(skill.name)
                                        }}
                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all"
                                    >
                                        <Trash2 className="w-3.5 h-3.5 text-gray-500" />
                                    </button>
                                }
                            </div>)
                        }
                    </div>
                </ExpandeBox> 
                <ExpandeBox 
                    title={
                        <div
                            className="flex items-center gap-2 hover:opacity-70 transition-opacity"
                        >
                            <Wrench className="w-4 h-4 text-gray-600" />
                            <span className="text-sm font-medium text-gray-800">Tools</span>
                            <span className="text-xs text-gray-400">({mcpTools?.length})</span>
                        </div>
                    }
                    hoverContent="New Tool"
                    onAdd={() => setToolConfigureOpen(true)}
                >
                    <div className="p-4 space-y-2">
                        {
                            mcpServers?.map((mcpServer, index) => <ServerCard 
                                key={`${mcpServer.name}-${index}`}
                                server={mcpServer}
                                handleDeleteMcpServer={handleDeleteMcpServer}
                                onRefresh={handleRefreshServer}
                            />)
                        }
                    </div>
                </ExpandeBox>  
            </>
        }

        <SkillConfigureModal 
            open={skillConfigureOpen}
            skillName={selectedSkillName}
            mcpTools={mcpTools}
            onSuccess={() => {
                handleCloseSkillEditor(true)
            }}
            onClose={() => {
                handleCloseSkillEditor(false)
            }}
        />

        <ToolConfigureModal
            open={toolConfigureOpen}
            server={mcpServers[selectedMcpServerIndex] || null}
            onSuccess={handleGetMcpServers}
            onClose={() => {
                setSelectedMcpServerIndex(-1)
                setToolConfigureOpen(false)
            }}
        />
    </div>
}

export default SkillsPanel