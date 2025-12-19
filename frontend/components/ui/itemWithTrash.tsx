import { Trash2 } from "lucide-react"
import { MouseEventHandler, ReactNode } from "react"

interface IProps {
    onItem?: MouseEventHandler<HTMLDivElement>
    onTrash?: MouseEventHandler<HTMLButtonElement>
    children?: ReactNode
    className?: string
}

const ItemWithTrash: React.FC<IProps> = (props) => {
    const { onItem = () => {}, onTrash = () => {}, children, className } = props

    return <div 
        onClick={onItem}
        className={`group flex items-center gap-1 px-4 py-2 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors ${className}`}
    >
        <div className="flex-1 min-w-0">
            {children}
        </div>
        <button
            onClick={onTrash}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all"
        >
            <Trash2 className="w-4 h-4 text-gray-500" />
        </button>
    </div>
}

export default ItemWithTrash