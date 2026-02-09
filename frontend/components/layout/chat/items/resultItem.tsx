'use client';

import MarkDown from '@/components/ui/markDown';
import { Sparkles, CheckCircle2, XCircle, Clock, FileText, AlertCircle, Bot } from 'lucide-react';
import { useState } from 'react';

interface IProps {
    content: any;
    status?: string;
    totalIterations?: number;
}

const ResultItem: React.FC<IProps> = (props) => {
    const { content, status = 'success', totalIterations } = props;
    
    const isSuccess = status === 'success';
    
    // Parse content if it's a stringified result
    let displayContent = content;
    let answer = '';
    let resultData = null;
    
    if (typeof content === 'string') {
        // Try to extract meaningful content from the string
        // Check if it contains JSON
        const jsonMatch = content.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            try {
                resultData = JSON.parse(jsonMatch[0]);
                if (resultData.answer) {
                    answer = resultData.answer;
                } else if (resultData.result) {
                    displayContent = resultData.result;
                }
            } catch {
                // Not valid JSON, use as is
            }
        }
        
        // Clean up the display content
        if (!answer) {
            // Remove common prefixes like "🎉 Final result (X iterations): success\n"
            displayContent = content.replace(/^[🎉❌]\s*Final result.*?:\s*(success|failed|error)\n?/i, '');
        }
    } else if (typeof content === 'object') {
        resultData = content;
        if (content.answer) {
            answer = content.answer;
        } else if (content.result) {
            displayContent = content.result;
        }
    }

    // Use answer if available, otherwise use displayContent
    const finalContent = answer || displayContent;

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
                <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 overflow-hidden">
                    {/* Header */}
                    <div className={`px-4 py-2 border-b ${isSuccess ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {isSuccess ? (
                                    <Sparkles className="w-4 h-4 text-green-600" />
                                ) : (
                                    <AlertCircle className="w-4 h-4 text-red-600" />
                                )}
                                <span className={`text-sm font-medium ${isSuccess ? 'text-green-700' : 'text-red-700'}`}>
                                    {isSuccess ? 'Task Complete' : 'Task Failed'}
                                </span>
                                {totalIterations && (
                                    <span className="flex items-center gap-1 text-xs text-gray-500">
                                        <Clock className="w-3 h-3" />
                                        {totalIterations} iterations
                                    </span>
                                )}
                            </div>
                            <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                                isSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>
                                {isSuccess ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                {isSuccess ? 'Success' : 'Failed'}
                            </div>
                        </div>
                    </div>
                    
                    {/* Content */}
                    <div className="p-4">
                        {typeof finalContent === 'string' ? (
                            <div className="prose prose-sm max-w-none">
                                <MarkDown content={finalContent} />
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {typeof finalContent === 'object' && finalContent !== null ? (
                                    Object.entries(finalContent).map(([key, value]) => (
                                        <div key={key} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                                            <div className="flex items-center justify-center w-6 h-6 rounded bg-gray-200 text-gray-600 shrink-0">
                                                <FileText className="w-3 h-3" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <span className="text-xs font-medium text-gray-600 block mb-0.5">{key}</span>
                                                <span className="text-sm text-gray-700 wrap-break-word">
                                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-gray-700">{String(finalContent)}</p>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResultItem;
