/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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

    // 格式化JSON字符串，处理可能的解析错误
    const formatJson = (data: any): string => {
        if (typeof data === 'string') {
            try {
                const parsed = JSON.parse(data);
                return JSON.stringify(parsed, null, 2);
            } catch {
                return data;
            }
        }
        return JSON.stringify(data, null, 2);
    };

    // 渲染代码块
    const renderCodeBlock = (code: string, title: string) => (
        <div className="bg-gray-50 rounded p-2">
            <div className="text-xs font-medium text-gray-600 mb-1">{title}:</div>
            <CodeHighlighter 
                language="json"
                code={code}
            />
        </div>
    );

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
                    {!isResult && hasArguments && renderCodeBlock(formatJson(toolCall.arguments), "参数")}
                    {isResult && hasResult && (renderCodeBlock(formatJson(toolCall.result), "结果"))}
                </div>
            )}
        </div>
    );
};

export default ToolCallItem;
