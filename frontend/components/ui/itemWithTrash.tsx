import { Trash2 } from "lucide-react"
import { MouseEventHandler, ReactNode, useState } from "react"
import PopoverCheck from "./popoverCheck"

interface IProps {
    selected?: boolean
    onItem?: MouseEventHandler<HTMLElement>
    onTrash?: () => void
    children?: ReactNode
    className?: string
}

const ItemWithTrash: React.FC<IProps> = (props) => {
    const { selected = false, onItem = () => {}, onTrash, children, className } = props

    const [isOpen, setIsOpen] = useState<boolean>(false)
    const [isInParent, setIsInParent] = useState<boolean>(false)
    
    return <div 
        onClick={onItem}
        className={`group flex items-center gap-1 px-4 py-2 rounded-lg ${selected ? "bg-gray-100" : ""} hover:bg-gray-100 cursor-pointer transition-colors ${className}`}
        // onMouseEnter={() => setIsInParent?.(true)}
        // onMouseLeave={() => setIsInParent?.(false)}
    >
        <div className="flex-1 min-w-0">
            {children}
        </div>
        <PopoverCheck
            content="是否删除？"
            onConfirm={onTrash}
            setIsOpen={setIsOpen}
            // isInParent={isInParent}
            buttonClassName={`${isOpen ? "opacity-100" : "opacity-0"} group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all`}
            buttonContent={<Trash2 className="w-4 h-4 text-gray-800" />}
        />
    </div>
}

export default ItemWithTrash