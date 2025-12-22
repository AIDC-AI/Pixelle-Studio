import ItemWithTrash from "@/components/ui/itemWithTrash"
import { useApp } from "@/context"
import { formatTime } from "@/utils/utils"
import { Book, Plus } from "lucide-react"

const ChatPanel = () => {
    const { 
        activeSessionId,
        setActiveSessionId, 
        sessions, 
        deleteSession
    } = useApp()
    
    const handleNewSession = () => {
        setActiveSessionId('')
    }

    return <div className="left-panel p-4 gap-4">
        {/* Knowledge Base */}
        <div className="p-4 bg-default rounded-lg border border-border-default">
            <div className="flex items-center gap-2 text-text-disabled">
                <Book className="w-4 h-4" />
                <span className="text-sm">个人知识库</span>
                <span className="ml-auto text-xs">即将上线</span>
            </div>
        </div> 

        {/* New Chat Button */}
        <button 
            className="w-full flex items-center gap-2 px-4 py-2.5 bg-default hover:bg-hover rounded-lg transition-colors text-text-default"
            onClick={handleNewSession}
        >
            <Plus className="w-4 h-4"/>
            <span className="font-default">新建对话</span>
        </button>

        {/* Chat History */}
        <div>
            <h3 className="font-title text-text-default mb-2">对话历史</h3>
            <div className="space-y-2">
                {
                    sessions?.map((session) => (
                        <ItemWithTrash
                            key={session.id}
                            selected={activeSessionId === session.id}
                            onItem={(e) => {
                                e.stopPropagation()
                                console.log('onItem-->')
                                setActiveSessionId(session.id)
                            }}
                            onTrash={() => {
                                deleteSession(session.id)
                            }}
                        >
                            <div className="flex flex-col">
                                <span className="font-default text-text-default">{session.title}</span>
                                <span className="font-title text-text-disabled">{formatTime(session.timestamp)}</span>
                            </div>
                        </ItemWithTrash>
                    ))
                }
            </div>
        </div>
    </div>
}

export default ChatPanel