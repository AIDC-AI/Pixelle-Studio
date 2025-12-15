import { useState } from "react";
import FlexBox from "./ui/flexBox";
import McpServers from "./mcpServers";

interface BoxProps {
    title: string;
    children?: React.ReactNode;
}

const BOX_LIST: BoxProps[] = [
    {
        title: 'Chat'
    },
    {
        title: 'Docs'
    },
    {
        title: 'Historys'
    },
    {
        title: 'Mcp Servers',
        children: <McpServers />
    }
]

const LeftPanel = () => {
    const [selectedIndex, setSelectedIndex] = useState<number>(-1);

    return <div className="w-[40%] bg-transparent h-full border-r border-gray-200 p-4 overflow-y-auto gap-8 flex flex-col">
        {
            BOX_LIST.map((item: BoxProps, index) => <FlexBox
                key={item.title}
                title={item.title}
                isFlex={index > 0}
                isSelected={index === selectedIndex}
                onSelect={() => {
                    if (index === selectedIndex) {
                        setSelectedIndex(-1);
                        return;
                    }
                    setSelectedIndex(index);
                }}
            >
                {item.children}
            </FlexBox>)
        }
    </div>
}

export default LeftPanel;