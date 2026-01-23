'use client';

import CodeHighlighter from '@/components/ui/codeHighlighter';
import { Wrench, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface IProps {
    toolCall?: {
        name: string;
        arguments?: Record<string, any>;
        result?: any;
        call_id?: string;
    };
    isResult?: boolean;
}

const ToolCallItem: React.FC<IProps> = ({ toolCall, isResult = false }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!toolCall) return null;

    const hasArguments = toolCall.arguments && Object.keys(toolCall.arguments).length > 0;
    const hasResult = toolCall.result !== undefined;

    return (
        <div className="text-xs">
            {/* Tool call header */}
            <div 
                className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors ${
                    isResult 
                        ? 'bg-green-50 hover:bg-green-100 text-green-700' 
                        : 'bg-blue-50 hover:bg-blue-100 text-blue-700'
                }`}
                onClick={() => (hasArguments || hasResult) && setIsExpanded(!isExpanded)}
            >
                <div className={`shrink-0 ${isResult ? 'text-green-600' : 'text-blue-600'}`}>
                    {isResult ? <CheckCircle className="w-3.5 h-3.5" /> : <Wrench className="w-3.5 h-3.5" />}
                </div>
                <span className="flex-1 font-medium">
                    {isResult ? '✓ ' : '🔧 '}
                    {toolCall.name}
                    {!isResult && hasArguments && ' (...)'}
                </span>
                {(hasArguments || hasResult) && (
                    <div className="shrink-0 text-gray-400">
                        {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </div>
                )}
            </div>

            {/* Arguments/Result details */}
            {isExpanded && (
                <div className="mt-1 ml-4 pl-3 border-l-2 border-gray-200">
                    {!isResult && hasArguments && (
                        <div className="bg-gray-50 rounded p-2">
                            <div className="text-xs font-medium text-gray-600 mb-1">参数:</div>
                            {/* <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(toolCall.arguments, null, 2)}
                            </pre> */}
                            <CodeHighlighter 
                                language={"json"}
                                code={JSON.stringify(toolCall.arguments, null, 2)}
                            />
                        </div>
                    )}
                    {isResult && hasResult && (
                        <div className="bg-gray-50 rounded p-2">
                            <div className="text-xs font-medium text-gray-600 mb-1">结果:</div>
                            {/* <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap max-h-40 overflow-y-auto">
                                {typeof toolCall.result === 'string' 
                                    ? toolCall.result 
                                    : JSON.stringify(toolCall.result, null, 2)}
                            </pre> */}
                            <CodeHighlighter 
                                language={"json"}
                                code={typeof toolCall.result === 'string' 
                                    ? toolCall.result 
                                    : JSON.stringify(toolCall.result, null, 2)}
                            />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ToolCallItem;
