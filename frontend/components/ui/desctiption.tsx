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

import { HoverCard } from "radix-ui";
import { useEffect, useRef, useState } from "react";

interface IProps {
    lineCount?: number // 最大行数，默认3
    description?: string
}

// 超出最大行数时省略，同时hover时弹出气泡显示所有内容 不超出最大行数hover无效果
const Description: React.FC<IProps> = (props) => {
    const { lineCount = 3, description } = props

    const textRef = useRef<HTMLSpanElement>(null);
    const [isOverflow, setIsOverflow] = useState(false);

    useEffect(() => {
        const element = textRef.current;
        if (element) {
            // Check if content overflows (scrollHeight > clientHeight means overflow)
            setIsOverflow(element.scrollHeight > element.clientHeight);
        }
    }, [lineCount, description]);

    const content = (
        <span 
            ref={textRef}
            className="font-title text-gray-500"
            style={{
                display: '-webkit-box',
                WebkitLineClamp: lineCount,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
            }}
        >
            {description}
        </span>
    );

    // Only show tooltip if content overflows
    if (isOverflow && description) {
        return (
            <HoverCard.Root>
                <HoverCard.Trigger asChild>
                    {content}
                </HoverCard.Trigger>
                <HoverCard.Portal>
                    <HoverCard.Content 
                        className="HoverCardContent" 
                        sideOffset={5}
                        side="right"
                    >
                        <p className="w-100 bg-gray-50 text-gray-600 p-4 rounded-lg shadow-[inset_0_0_8px_#ccc]">
                            {
                                description
                            }
                        </p>
                        <HoverCard.Arrow fill="#fff" />
                    </HoverCard.Content>
                </HoverCard.Portal>
            </HoverCard.Root>
        );
    }

    return content;
};

export default Description;