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
        <div className="bg-gradient-to-br from-amber-50 to-yellow-50 border border-amber-200 rounded-xl overflow-hidden">
            {/* Header */}
            <div 
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-amber-100/50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-200/60 text-amber-600">
                        <Lightbulb className="w-4 h-4" />
                    </div>
                    <span className="font-medium text-amber-800">修改建议</span>
                </div>
                <div className="text-amber-600">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content */}
            {isExpanded && (
                <div className="px-4 pb-4">
                    <div className="bg-white/60 rounded-lg p-3 border border-amber-100">
                        <pre className="whitespace-pre-wrap text-sm text-amber-900 font-normal leading-relaxed">
                            {cleanContent}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdviceItem;
