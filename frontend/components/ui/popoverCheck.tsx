import { Popover } from "radix-ui"
import { Dispatch, ReactNode, SetStateAction, useEffect, useState } from "react"

interface IProps {
    title?: string | ReactNode
    content?: string | ReactNode
    onConfirm?: () => void
    setIsOpen?: Dispatch<SetStateAction<boolean>>
    isInParent?: boolean
    buttonContent?: ReactNode
    buttonClassName?: string
}

const PopoverCheck: React.FC<IProps> = (props) => {
    const {
        title,
        content = '',
        onConfirm,
        setIsOpen,
        isInParent,
        buttonContent,
        buttonClassName
    } = props

    const [open, setOpen] = useState<boolean>(false)

    useEffect(() => {
        if (!isInParent)
            setOpen(false)
    }, [isInParent])

    return <Popover.Root
        open={open}
        onOpenChange={setOpen}
    >
		<Popover.Trigger asChild>
			<button
                onClick={(e) => {
                    e.stopPropagation()
                    setOpen(true)
                }}
                className={buttonClassName}
            >
                {buttonContent}
            </button>
		</Popover.Trigger>
		<Popover.Portal>
			<Popover.Content 
                side="top" 
                className="p-4 bg-white rounded-lg" 
                sideOffset={5}
                onMouseEnter={() => setIsOpen?.(true)}
                onMouseLeave={() => setIsOpen?.(false)}
                onPointerDownOutside={(e) => {
                    e.stopPropagation()
                }}
            >
				<div className="flex flex-col gap-2">
                    {title}
					<span className="text-gray-900 text-sm">{content}</span>
                    <div className="flex flex-row justify-end gap-4 w-40">
                        <button 
                            className="flex justify-center items-center px-2 py-1 rounded border border-gray-200 bg-white text-gray-900 text-xs" 
                            onClick={(e) => {
                                e.stopPropagation()
                                setOpen(false)
                            }}
                        >
                            取消
                        </button>
                        <button 
                            className="flex justify-center items-center px-2 py-1 rounded border border-gray-200 bg-[#1677ff] text-white text-xs"
                            onClick={(e) => {
                                e.stopPropagation()
                                onConfirm?.()
                                setOpen(false)
                            }}
                        >
                            确定
                        </button>   
                    </div>
				</div>
				<Popover.Arrow fill="#fff" />
			</Popover.Content>
		</Popover.Portal>
	</Popover.Root>
}

export default PopoverCheck