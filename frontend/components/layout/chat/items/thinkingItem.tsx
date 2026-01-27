'use client';

import { Brain, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface IProps {
    content: string;
}

const ThinkingItem: React.FC<IProps> = (props) => {
    const { content } = props;
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div 
            className="bg-gray-100 border border-gray-200 rounded-lg overflow-hidden"
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)' }}
        >
            {/* Header - 可点击展开/折叠 */}
            <div 
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-150 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="flex items-center justify-center w-6 h-6 rounded bg-purple-100 text-purple-600 shrink-0">
                        <Brain className="w-3 h-3" />
                    </div>
                    <span className="text-xs font-medium text-gray-600">Thought</span>
                    {!isExpanded && (
                        <span className="text-xs text-gray-400 truncate flex-1 min-w-0">
                            {content.substring(0, 100)}{content.length > 100 ? '...' : ''}
                        </span>
                    )}
                </div>
                <div className="text-gray-500 shrink-0 ml-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content - 展开时显示完整内容 */}
            {isExpanded && (
                <div className="px-3 pb-3">
                    <div className="bg-white rounded p-2 border border-gray-200">
                        <pre className="whitespace-pre-wrap text-xs text-gray-700 font-normal leading-relaxed">
                            {content}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ThinkingItem;





