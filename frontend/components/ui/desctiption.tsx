import { Tooltip } from "antd";
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
            className="font-title text-text-disabled"
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
            <Tooltip 
                title={description} 
                placement="topRight"
                arrow={false}
                styles={{
                    container: {
                        width: 400,
                        padding: 12,
                        borderRadius: 12,
                        backgroundColor: "var(--color-default)",
                        color: "var(--color-text-default)",
                        boxShadow: 'inset 0 0 8px #ccc',
                    }
                }}
            >
                {content}
            </Tooltip>
        );
    }

    return content;
};

export default Description;