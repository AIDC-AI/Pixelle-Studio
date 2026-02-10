import { ChevronDown, ChevronUp, Plus } from "lucide-react"
import { HoverCard } from "radix-ui"
import { useState } from "react"

interface IProps {
    title?: string | React.ReactNode
    hoverContent?: string | React.ReactNode
    onAdd?: () => void
    children?: React.ReactNode
}

const ExpandeBox: React.FC<IProps> = (props) => {
    const { title, hoverContent, onAdd, children } = props

    const [isExpanded, setIsExpanded] = useState<boolean>(false)

    return <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ flexShrink: 0 }}>
        <div 
            className="flex items-center justify-between p-3 bg-gray-50"
            onClick={(e) => {
                e.stopPropagation()
                setIsExpanded(!isExpanded)
            }}
        >
            {title}
            <div className="flex flex-1 items-center justify-between pl-4">
                <HoverCard.Root>
                    <HoverCard.Trigger asChild>
                        <button
                            onClick={(e) => {
                                e.stopPropagation()
                                onAdd?.()
                            }}
                            className="hover:bg-gray-200 rounded transition-colors p-1"
                        >
                            <Plus className="w-4 h-4 text-gray-600" />
                        </button>
                    </HoverCard.Trigger>
                    {
                        hoverContent && <HoverCard.Portal>
                            <HoverCard.Content 
                                side="top" 
                                className="bg-white p-1 rounded-lg border border-gray-300" 
                                sideOffset={5}
                            >
                                <span className="text-gray-900 text-xs">{hoverContent}</span>
                                <HoverCard.Arrow 
                                    className="fill-gray-300 -translate-x-0.5" 
                                    width={14} 
                                    height={6} 
                                />
                                <HoverCard.Arrow 
                                    className="fill-white" 
                                    width={10} 
                                    height={5} 
                                />
                            </HoverCard.Content>
                        </HoverCard.Portal>
                    }
                    
                </HoverCard.Root>
                <button
                    className="rounded transition-colors p-1"
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