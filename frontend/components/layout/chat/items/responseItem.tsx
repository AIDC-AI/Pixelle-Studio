'use client';

import MarkDown from '@/components/ui/markDown';
import { Bot } from 'lucide-react';

interface IProps {
    content: string;
    isStreaming?: boolean;
}

const ResponseItem: React.FC<IProps> = (props) => {
    const { content } = props;

    return (
        <div className="flex gap-3">
            {/* Avatar */}
            <div className="shrink-0">
                <div className="w-8 h-8 rounded-xl bg-orange-500 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 px-4 py-3">
                    <div className="prose prose-slate max-w-none prose-sm">
                        <MarkDown content={content} codeColor="text-gray-700" />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResponseItem;
