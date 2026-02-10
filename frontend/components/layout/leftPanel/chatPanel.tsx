import ItemWithTrash from "@/components/ui/itemWithTrash"
import { useApp } from "@/context"
import { Session } from "@/types/session"
import { formatTime } from "@/utils/utils"
import { Book, Plus } from "lucide-react"

interface IProps {
    sessions?: Session[]
    handleNewSession?: (input: string) => void
    handleChangeSession?: (id: string) => void
    handleDeleteSession?: (id: string) => void
}

const ChatPanel: React.FC<IProps> = (props) => {
    const { sessions, handleChangeSession, handleDeleteSession } = props

    const {
        activeSessionId,
        setActiveSessionId
    } = useApp()

    const handleNewSession = () => {
        setActiveSessionId("")
        handleChangeSession?.('')
    }

    return <div style={{ display: 'flex', flexDirection: 'column', flex: '1 1 0%', minHeight: 0, overflowY: 'auto', padding: 16, gap: 16 }}>
        {/* Knowledge Base */}
        {/* <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2 text-gray-400">
                <Book className="w-4 h-4" />
                <span className="text-sm">Personal Knowledge Base</span>
                <span className="ml-auto text-xs">Coming soon</span>
            </div>
        </div> */}

        {/* New Chat Button */}
        <button
            className="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            onClick={() => {
                handleNewSession?.()
            }}
        >
            <Plus className="w-4 h-4" />
            <span className="font-default">New Chat</span>
        </button>

        {/* Chat History */}
        <div>
            {/* <h3 className="font-title text-gray-600 mb-2">Chat History</h3> */}
            <div className="space-y-2">
                {
                    sessions?.map((session) => (
                        <ItemWithTrash
                            key={session.id}
                            selected={activeSessionId === session.id}
                            onItem={(e) => {
                                e.stopPropagation()
                                handleChangeSession?.(session.id)
                            }}
                            onTrash={() => {
                                // If deleting the current session, set to empty chat
                                if (activeSessionId === session.id) {
                                    handleChangeSession?.('')
                                }
                                handleDeleteSession?.(session.id)
                            }}
                        >
                            <div className="flex flex-col">
                                <span className="font-default text-gray-800">{session.title}</span>
                                <span className="font-title text-gray-500">{formatTime(session.timestamp)}</span>
                            </div>
                        </ItemWithTrash>
                    ))
                }
            </div>
        </div>
    </div>
}

export default ChatPanel