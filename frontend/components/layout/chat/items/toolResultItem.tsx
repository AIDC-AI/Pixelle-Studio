// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

import { CheckCircle2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { ToolResultInfo } from '@/types/message';
import { useState } from 'react';

interface IProps {
    toolResult: ToolResultInfo;
}

const ToolResultItem: React.FC<IProps> = (props) => {
    const { toolResult } = props;
    const [isExpanded, setIsExpanded] = useState(false);

    // Determine if result indicates success or error
    const resultStr = String(toolResult.result || '');
    const isError = resultStr.toLowerCase().includes('**status**: error') || 
                    resultStr.toLowerCase().includes('not found') ||
                    resultStr.toLowerCase().includes('failed');
    
    // Check if result is long enough to need expansion
    const isLongResult = resultStr.length > 200;
    const displayResult = isExpanded || !isLongResult 
        ? resultStr 
        : resultStr.substring(0, 200) + '...';

    return (
        <div 
            className={`flex flex-col gap-2 px-3 py-2 border rounded-lg ${
                isError 
                    ? 'bg-red-50 border-red-200' 
                    : 'bg-emerald-50 border-emerald-200'
            }`}
        >
            <div className="flex items-center gap-2">
                <div className={`flex items-center justify-center w-5 h-5 rounded ${
                    isError ? 'bg-red-100 text-red-500' : 'bg-emerald-100 text-emerald-500'
                }`}>
                    {isError ? (
                        <XCircle className="w-3.5 h-3.5" />
                    ) : (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                </div>
                <span className={`text-xs font-medium ${
                    isError ? 'text-red-700' : 'text-emerald-700'
                }`}>
                    {toolResult.name} {isError ? 'failed' : 'completed'}
                </span>
            </div>
            
            {/* Result content */}
            <div className="pl-7">
                <pre className={`text-xs whitespace-pre-wrap font-mono ${
                    isError ? 'text-red-600' : 'text-emerald-700'
                } bg-white/50 rounded p-2 overflow-x-auto`}>
                    {displayResult}
                </pre>
                
                {isLongResult && (
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className={`flex items-center gap-1 mt-1 text-xs ${
                            isError ? 'text-red-500 hover:text-red-700' : 'text-emerald-500 hover:text-emerald-700'
                        }`}
                    >
                        {isExpanded ? (
                            <>
                                <ChevronUp className="w-3 h-3" />
                                Show less
                            </>
                        ) : (
                            <>
                                <ChevronDown className="w-3 h-3" />
                                Show more
                            </>
                        )}
                    </button>
                )}
            </div>
        </div>
    );
};

export default ToolResultItem;
