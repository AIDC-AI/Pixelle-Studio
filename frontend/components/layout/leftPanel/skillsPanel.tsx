import { Book, Trash2, Wrench } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { ScriptItem, Skill } from "@/types/skill";
import { api } from "@/lib/api";
import SkillConfigureModal from "@/components/ui/skillConfigureModal";
import ExpandeBox from "@/components/ui/expandeBox";
import { useApp } from "@/context";
import { mcpServerAPI } from "@/lib/mcpServerApi";
import ToolConfigureModal from "@/components/ui/toolConfigureModal";
import { MCPServer } from "@/types/server";
import ServerCard from "@/components/ui/serverCard";
import { Skeleton } from "antd";

const SkillsPanel = () => {
    const { messageApi, setSkillEditored } = useApp()

    const [loading, setLoading] = useState<boolean>(false);

    const [mcpServers, setMcpServers] = useState<MCPServer[]>([])
    const [skillConfigureOpen, setSkillConfigureOpen] = useState<boolean>(false)
    const [toolConfigureOpen, setToolConfigureOpen] = useState<boolean>(false)
    const [skills, setSkills] = useState<Skill[]>([])

    const [selectedIndex, setSelectedIndex] = useState<number>(-1)
    const [selectedSkillIndex, setSelectedSkillIndex] = useState<number>(-1)
    const [selectedMcpServerIndex, setSelectedMcpServerIndex] = useState<number>(-1)

    const handleShowSkillEditor = () => {
        // setSkillEditored(true)
        setSkillConfigureOpen(true)
    }

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

    const handleDeleteSkill = async (id: string) => {
        setLoading(true);

        try {
            await api.deleteSkill(id);
            messageApi.success('Delete Skill Successed!')
        } catch (error) {
            console.error(`Failed to fetch skills:`, error);
            messageApi.error((error as Error).message || 'Delete Skill Failed!')
        }

        setLoading(false);
    }

    const handleGetMcpServers = async () => {
        setLoading(true);

        try {
            const res = await mcpServerAPI.getServers(true); // 获取包含状态和工具的数据
            if (!!res) {
                setMcpServers(res);
            }
        } catch (error) {
            console.error('Failed to fetch MCP servers:', error);
            messageApi.error((error as Error).message || '获取服务器列表失败');
        }

        setLoading(false);
    };

    const handleDeleteMcpServer = async (id: string) => {
        try {
            await mcpServerAPI.deleteServer(id);
            setMcpServers(prev => [...prev.filter((server) => server.id !== id)])
            messageApi.success('Delete McpServer Successed!')
        } catch (error) {
            messageApi.error((error as Error).message || 'Delete McpServer Failed!')
        }
    };

    const handleRefreshServer = async (serverId: string) => {
        // 标记服务器为检查中状态
        setMcpServers(prev => prev.map(s => 
            s.id === serverId ? { ...s, status: 'checking' as const } : s
        ));

        try {
            const status = await mcpServerAPI.checkServerStatus(serverId);
            // 更新服务器状态和工具
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

    // 总的工具数量
    const totalTools = useMemo(() => {
        return mcpServers.reduce<ScriptItem[]>((total, server) => [...total, ...(server?.tools.map((tool) => ({
            serverId: server.id,
            serverName: server.name,
            toolName: tool.name
        })) || [])], [])
    }, [mcpServers])

    return <div className="left-panel p-4 gap-4">
        {
            loading ? <Skeleton /> : <>
                <ExpandeBox 
                    title={
                        <div
                            className="flex items-center gap-2 hover:opacity-70 transition-opacity"
                        >
                            <Book className="w-4 h-4 text-gray-600" />
                            <span className="text-sm font-medium text-gray-800">技能</span>
                            <span className="text-xs text-gray-400">({skills?.length || 0})</span>
                        </div>
                    }
                    onAdd={handleShowSkillEditor}
                >
                    <div className="p-4 space-y-2">
                        {
                            skills?.map((skill, index) => <div
                                key={skill.id}
                                onClick={() => {
                                    handleShowSkillEditor()
                                }}
                                className="group flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                            >
                                <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <p className="text-sm text-gray-800 truncate">{skill.name}</p>
                                </div>
                                <p className="text-xs text-gray-500 truncate">{skill.description}</p>
                                </div>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteSkill(skill.id)
                                    }}
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all"
                                >
                                    <Trash2 className="w-3.5 h-3.5 text-gray-500" />
                                </button>
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
                            <span className="text-sm font-medium text-gray-800">工具</span>
                            <span className="text-xs text-gray-400">({totalTools?.length})</span>
                        </div>
                    }
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
            skill={skills[selectedSkillIndex] || null}
            scripts={totalTools}
            onSuccess={handleGetSkills}
            onClose={() => {
                setSelectedSkillIndex(-1)
                setSkillConfigureOpen(false)
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