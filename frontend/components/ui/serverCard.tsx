import { MCPServer } from "@/types/server"
import { Check, RefreshCw, Trash2 } from "lucide-react";

interface IProps {
    server: MCPServer
    handleDeleteMcpServer?: (id: string) => void
    onRefresh?: (serverId: string) => void
}

const ServerCard: React.FC<IProps> = (props) => {
    const { server, handleDeleteMcpServer, onRefresh } = props
    
    return <div className="border border-gray-100 rounded-lg p-2">
        <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${
                server.status === 'connected' ? 'bg-green-500' : 
                server.status === 'error' ? 'bg-red-500' : 
                server.status === 'checking' ? 'bg-yellow-500' : 'bg-gray-400'
            }`} />
            <span className="text-sm font-medium text-gray-800">{server.name}</span>
            <div className="flex-1" />
            {onRefresh && (
                <button
                    onClick={() => onRefresh(server.id)}
                    className="p-1 hover:bg-gray-100 rounded transition-colors"
                    title="Refresh status"
                    disabled={server.status === 'checking'}
                >
                    <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${server.status === 'checking' ? 'animate-spin' : ''}`} />
                </button>
            )}
            <button
                onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteMcpServer?.(server.id)
                }}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
                <Trash2 className="w-3.5 h-3.5 text-gray-500" />
            </button>
        </div>
        
        {server.status === 'error' && server.message && (
            <p className="text-xs text-red-500 mb-1">{server.message}</p>
        )}
        
        {server.status === 'connected' && (
            <p className="text-xs text-gray-500 mb-1">
                {server.message} ({server.response_time}ms)
            </p>
        )}
        
        {server.tools?.length > 0 && (
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
}

export default ServerCard