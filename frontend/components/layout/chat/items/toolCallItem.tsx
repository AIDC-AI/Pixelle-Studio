'use client';

import { Wrench, ChevronRight } from 'lucide-react';
import { ToolCallInfo } from '@/types/message';

interface IProps {
    toolCall: ToolCallInfo;
}

const ToolCallItem: React.FC<IProps> = (props) => {
    const { toolCall } = props;

    // Format arguments for display
    const formatArgs = (args: Record<string, any>): string => {
        if (!args || Object.keys(args).length === 0) {
            return 'No arguments';
        }
        
        // For code arguments, truncate
        if (args.code) {
            const codePreview = args.code.length > 50 
                ? args.code.substring(0, 50) + '...' 
                : args.code;
            return `code: "${codePreview}"`;
        }
        
        // For other arguments
        return Object.entries(args)
            .map(([key, value]) => {
                const strValue = typeof value === 'string' 
                    ? value.length > 30 ? value.substring(0, 30) + '...' : value
                    : JSON.stringify(value);
                return `${key}: ${strValue}`;
            })
            .join(', ');
    };

    // Tool name to icon color mapping
    const getToolColor = (name: string): string => {
        switch (name) {
            case 'load_skill':
                return 'bg-purple-100 text-purple-600 border-purple-200';
            case 'execute_code':
                return 'bg-amber-100 text-amber-600 border-amber-200';
            case 'read_skill_file':
                return 'bg-blue-100 text-blue-600 border-blue-200';
            case 'list_skill_tree':
                return 'bg-cyan-100 text-cyan-600 border-cyan-200';
            case 'list_mcp_tools':
                return 'bg-emerald-100 text-emerald-600 border-emerald-200';
            default:
                return 'bg-gray-100 text-gray-600 border-gray-200';
        }
    };

    const colorClass = getToolColor(toolCall.name);

    return (
        <div 
            className={`flex items-center gap-2 px-3 py-2 border rounded-lg ${colorClass}`}
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)' }}
        >
            <div className="flex items-center justify-center w-6 h-6 rounded bg-white/50">
                <Wrench className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold">
                        {toolCall.name}
                    </span>
                    <ChevronRight className="w-3 h-3 opacity-50" />
                    <span className="text-xs opacity-75 truncate">
                        {formatArgs(toolCall.arguments)}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default ToolCallItem;
