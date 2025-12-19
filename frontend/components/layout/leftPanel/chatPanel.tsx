import ItemWithTrash from "@/components/ui/itemWithTrash"
import { useApp } from "@/context"
import { formatTime } from "@/utils/utils"
import { Book, Plus } from "lucide-react"

const ChatPanel = () => {
    const { 
        setActiveSessionId, 
        sessions, 
        deleteSession
    } = useApp()
    
    const handleNewSession = () => {
        setActiveSessionId('')
    }

    return <div className="p-4">
        {/* Knowledge Base */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2 text-gray-400">
                <Book className="w-4 h-4" />
                <span className="text-sm">个人知识库</span>
                <span className="ml-auto text-xs">即将上线</span>
            </div>
        </div> 

        {/* New Chat Button */}
        <button 
            className="w-full flex items-center gap-2 px-4 py-2.5 mb-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-gray-700"
            onClick={handleNewSession}
        >
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium">新建对话</span>
        </button>

        {/* Chat History */}
        <div>
            <h3 className="text-xs font-medium text-gray-500 mb-2 px-2">对话历史</h3>
            <div className="space-y-1">
                {
                    sessions?.reverse()?.map((session) => (
                        <ItemWithTrash
                            key={session.id}
                            onItem={(e) => {
                                e.stopPropagation()
                                setActiveSessionId(session.id)
                            }}
                            onTrash={(e) => {
                                e.stopPropagation()
                                deleteSession(session.id)
                            }}
                        >
                            <div className="flex flex-col">
                                <span className="item-title">{session.title}</span>
                                <span className="item-subtitle">{formatTime(session.timestamp)}</span>
                            </div>
                        </ItemWithTrash>
                    ))
                }
            </div>
        </div>
    </div>
}

export default ChatPanel