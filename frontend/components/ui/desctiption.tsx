import { HoverCard } from "radix-ui";
import { useEffect, useRef, useState } from "react";

interface IProps {
    lineCount?: number // Max number of lines, default 3
    description?: string
}

// Truncate when exceeding max lines, show full content in hover popover; no hover effect if not overflowing
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