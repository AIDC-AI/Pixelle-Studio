'use client';

import { Sparkles, CheckCircle2, XCircle, Clock, FileText, AlertCircle, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

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
            <div className="flex-shrink-0">
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
                                    {isSuccess ? '任务完成' : '任务失败'}
                                </span>
                                {totalIterations && (
                                    <span className="flex items-center gap-1 text-xs text-gray-500">
                                        <Clock className="w-3 h-3" />
                                        {totalIterations} 次迭代
                                    </span>
                                )}
                            </div>
                            <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                                isSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>
                                {isSuccess ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                {isSuccess ? '成功' : '失败'}
                            </div>
                        </div>
                    </div>
                    
                    {/* Content */}
                    <div className="p-4">
                        {typeof finalContent === 'string' ? (
                            <div className="prose prose-sm max-w-none">
                                <ReactMarkdown
                                    components={{
                                        p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-3 last:mb-0">{children}</p>,
                                        h1: ({ children }) => <h1 className="text-lg font-bold text-gray-800 mb-2">{children}</h1>,
                                        h2: ({ children }) => <h2 className="text-base font-bold text-gray-800 mb-2">{children}</h2>,
                                        h3: ({ children }) => <h3 className="text-sm font-bold text-gray-800 mb-2">{children}</h3>,
                                        ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3 text-gray-700">{children}</ul>,
                                        ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3 text-gray-700">{children}</ol>,
                                        li: ({ children }) => <li className="text-gray-700">{children}</li>,
                                        strong: ({ children }) => <strong className="font-bold text-gray-800">{children}</strong>,
                                        em: ({ children }) => <em className="text-gray-600 italic">{children}</em>,
                                        code: ({ children }) => (
                                            <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-700">
                                                {children}
                                            </code>
                                        ),
                                        pre: ({ children }) => (
                                            <pre className="bg-gray-800 text-gray-200 p-3 rounded-lg overflow-x-auto my-3 font-mono text-xs">
                                                {children}
                                            </pre>
                                        ),
                                        blockquote: ({ children }) => (
                                            <blockquote className="border-l-3 border-gray-300 pl-3 py-1 my-3 bg-gray-50 rounded-r-lg italic text-gray-600 text-sm">
                                                {children}
                                            </blockquote>
                                        ),
                                    }}
                                >
                                    {finalContent}
                                </ReactMarkdown>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {typeof finalContent === 'object' && finalContent !== null ? (
                                    Object.entries(finalContent).map(([key, value]) => (
                                        <div key={key} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                                            <div className="flex items-center justify-center w-6 h-6 rounded bg-gray-200 text-gray-600 flex-shrink-0">
                                                <FileText className="w-3 h-3" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <span className="text-xs font-medium text-gray-600 block mb-0.5">{key}</span>
                                                <span className="text-sm text-gray-700 break-words">
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
