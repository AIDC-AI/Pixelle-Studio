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
        <div 
            className={`flex items-start gap-2 px-3 py-1.5 rounded font-mono text-xs ${
                isStderr 
                    ? 'bg-amber-50 border border-amber-200' 
                    : 'bg-gray-100 border border-gray-200'
            }`}
            style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.06)' }}
        >
            <Terminal className={`w-3 h-3 mt-0.5 flex-shrink-0 ${
                isStderr ? 'text-amber-500' : 'text-gray-400'
            }`} />
            <span className={isStderr ? 'text-amber-700' : 'text-gray-600'}>
                {cleanContent}
            </span>
        </div>
    );
};

export default LogItem;
