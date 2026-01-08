import { ChevronDown, ChevronUp, Plus } from "lucide-react"
import { useState } from "react"

interface IProps {
    title?: string | React.ReactNode
    onAdd?: () => void
    children?: React.ReactNode
}

const ExpandeBox: React.FC<IProps> = (props) => {
    const { title, onAdd, children } = props

    const [isExpanded, setIsExpanded] = useState<boolean>(false)

    return <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-3 bg-gray-50">
            {title}
            <div className="flex flex-1 items-center justify-between pl-4">
                <button
                    onClick={(e) => {
                        e.stopPropagation()
                        onAdd?.()
                    }}
                    className="hover:bg-gray-200 rounded transition-colors p-1"
                >
                    <Plus className="w-4 h-4 text-gray-600" />
                </button>
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="hover:bg-gray-200 rounded transition-colors p-1"
                >
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                </button>
            </div>
        </div>
        {
            isExpanded && children
        }
    </div>
}

export default ExpandeBox