import { useApp } from "@/context";
import { useMCPServer } from "@/hooks/useMCPServer";
import { mcpServerAPI } from "@/lib/mcpServerApi";
import { MCPServer } from "@/types/server"
import { Check, Link, Trash2 } from "lucide-react";
import { useEffect } from "react";

interface IProps {
    server: MCPServer
}

const ServerCard: React.FC<IProps> = (props) => {
    const { server } = props
    const { messageApi } = useApp()
    
    const {
        tools,
        fetchTools,
        status,
        statusError,
        checkStatus
    } = useMCPServer(server.id, {
        autoCheckStatus: true,  // 自动检查状态
        statusInterval: 60000,  // 每 60 秒检查一次
        autoLoadTools: false    // 手动加载工具
    });

    const handleDeleteMcpServer = async (id: string) => {
        try {
            const res = mcpServerAPI.deleteServer(id)
            if (!!res) {
                messageApi.success('Delete McpServer Successed!')
            } else {
                messageApi.error(res || 'Delete McpServer Failed!')
            }
        } catch (error) {
            messageApi.error((error as Error).message || 'Delete McpServer Failed!')
        }
    }

    useEffect(() => {
        fetchTools()
    }, [])

    return <div className="border border-gray-100 rounded-lg p-2">
        <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${
                status?.status === 'connected' ? 'bg-green-500' : 
                status?.status === 'error' ? 'bg-red-500' : 'bg-gray-400'
            }`} />
            <span className="text-sm font-medium text-gray-800">{server.name}</span>
            <div className="flex-1" />
            <button
                onClick={() => checkStatus(server.id)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="测试连接"
            >
                <Link className="w-3.5 h-3.5 text-gray-500" />
            </button>
            <button
                onClick={(e) => handleDeleteMcpServer(server.id, e)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
                <Trash2 className="w-3.5 h-3.5 text-gray-500" />
            </button>
        </div>
        
        {statusError && (
            <p className="text-xs text-red-500 mb-1">{statusError}</p>
        )}
        
        {tools?.length > 0 && (
            <div className="pl-4 space-y-1">
            {tools.map((tool, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-gray-600">
                <Check className="w-3 h-3 text-green-500" />
                <span>{tool.name}</span>
                </div>
            ))}
            </div>
        )}
    </div>
}

export default ServerCard