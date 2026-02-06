/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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