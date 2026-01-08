'use client';

import { Terminal } from 'lucide-react';

interface IProps {
    content?: string;
}

const LogItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    // Parse log type from content (e.g., "[stdout] message" or "[stderr] message")
    const isStderr = content.toLowerCase().includes('[stderr]');
    const cleanContent = content.replace(/^\[(stdout|stderr|LOG)\]\s*/i, '');

    return (
        <div className={`flex items-start gap-2 px-3 py-2 rounded-lg font-mono text-xs ${
            isStderr 
                ? 'bg-amber-50 border border-amber-200' 
                : 'bg-slate-50 border border-slate-200'
        }`}>
            <Terminal className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                isStderr ? 'text-amber-500' : 'text-slate-400'
            }`} />
            <span className={isStderr ? 'text-amber-700' : 'text-slate-600'}>
                {cleanContent}
            </span>
        </div>
    );
};

export default LogItem;
