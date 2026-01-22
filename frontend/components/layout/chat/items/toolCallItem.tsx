'use client';

import { Wrench, ChevronRight, ChevronDown } from 'lucide-react';
import { ToolCallInfo } from '@/types/message';
import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface IProps {
    toolCall: ToolCallInfo;
}

const ToolCallItem: React.FC<IProps> = (props) => {
    const { toolCall } = props;
    const [isExpanded, setIsExpanded] = useState<boolean>(false)

    // Format arguments for display
    const formatArgs = (args: Record<string, any>): string => {
        if (!args || Object.keys(args).length === 0) {
            return 'No arguments';
        }
        
        // For code arguments, show lines count and preview
        if (args.code) {
            const code = args.code as string;
            const lines = code.split('\n').length;
            const firstLine = code.split('\n')[0]?.trim() || '';
            const preview = firstLine.length > 60 
                ? firstLine.substring(0, 60) + '...' 
                : firstLine;
            return `${lines} lines: ${preview}`;
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

    const formatExpandedArgs = (args: Record<string, any>): React.ReactNode => {
        let language = "python"
        let str = ""
        if (args.code) {
            str = args.code
        } else {
            language = "json"
            str = JSON.stringify(args)
        }
        return <div className="relative overflow-auto max-h-100">
            <SyntaxHighlighter
                language={language}
                style={vs}
                customStyle={{
                    margin: 0,
                    padding: '0.75rem',
                    background: '#ffffff',
                    fontSize: '0.75rem',
                    lineHeight: '1.25rem',
                    borderRadius: '0.375rem',
                }}
                showLineNumbers
                lineNumberStyle={{
                    minWidth: '2.5em',
                    paddingRight: '0.75em',
                    color: '#9ca3af',
                    userSelect: 'none',
                    fontSize: '0.7rem',
                }}
                wrapLines
            >
                {str}
            </SyntaxHighlighter>
        </div>
    }

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
            className={`flex flex-col justify-center gap-2 px-3 py-2 border rounded-lg ${colorClass}`}
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)' }}
        >
            <div className="flex flex-row justify-center items-center">
                <div className="flex items-center justify-center w-6 h-6 rounded bg-white/50">
                    <Wrench className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0 flex flex-col">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold">
                            {toolCall.name}
                        </span>
                        <button
                            onClick={() => {
                                setIsExpanded(!isExpanded)
                            }}
                        >
                            {
                                isExpanded ? <ChevronDown className="w-3 h-3 opacity-50" /> : 
                                <ChevronRight className="w-3 h-3 opacity-50" />
                            }
                        </button>
                        {
                            !isExpanded && <span className="text-xs opacity-75 truncate">
                                {formatArgs(toolCall.arguments)}
                            </span>
                        }
                    </div>
                </div>
            </div>
            {
                isExpanded && formatExpandedArgs(toolCall.arguments)
            }
        </div>
    );
};

export default ToolCallItem;
