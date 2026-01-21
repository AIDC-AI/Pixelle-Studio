'use client';

import { Lightbulb, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface IProps {
    content?: string;
}

const AdviceItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;
    const [isExpanded, setIsExpanded] = useState(true);

    // Clean up content
    const cleanContent = content.replace(/^💡\s*Revision advice.*?:\n?/i, '');

    return (
        <div 
            className="bg-gray-100 border border-gray-200 rounded-lg overflow-hidden"
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)' }}
        >
            {/* Header */}
            <div 
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-150 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-6 h-6 rounded bg-gray-300 text-gray-600">
                        <Lightbulb className="w-3 h-3" />
                    </div>
                    <span className="text-xs font-medium text-gray-600">修改建议</span>
                </div>
                <div className="text-gray-500">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content */}
            {isExpanded && (
                <div className="px-3 pb-3">
                    <div className="bg-white rounded p-2 border border-gray-200">
                        <pre className="whitespace-pre-wrap text-xs text-gray-700 font-normal leading-relaxed">
                            {cleanContent}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdviceItem;
