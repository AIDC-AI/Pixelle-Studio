import { Popconfirm } from "antd"
import { Trash2 } from "lucide-react"
import { MouseEventHandler, ReactNode } from "react"

interface IProps {
    selected?: boolean
    onItem?: MouseEventHandler<HTMLElement>
    onTrash?: () => void
    children?: ReactNode
    className?: string
}

const ItemWithTrash: React.FC<IProps> = (props) => {
    const { selected = false, onItem = () => {}, onTrash, children, className } = props

    return <div 
        onClick={onItem}
        className={`group flex items-center gap-1 px-4 py-2 rounded-lg ${selected ? "bg-gray-100" : ""} hover:bg-gray-100 cursor-pointer transition-colors ${className}`}
    >
        <div className="flex-1 min-w-0">
            {children}
        </div>
        <Popconfirm
            title="Delete"
            description="Are you sure to delete?"
            onConfirm={(e) => {
                e?.stopPropagation()
                onTrash?.()
            }}
            onCancel={(e) => {
                e?.stopPropagation()
            }}
            okText="Yes"
            cancelText="No"
        >   
            <button
                onClick={(e) => e.stopPropagation()}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all"
            >
                <Trash2 className="w-4 h-4 text-gray-800" />
            </button>
        </Popconfirm>
    </div>
}

export default ItemWithTrash