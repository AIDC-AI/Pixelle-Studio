'use client';

import { Sparkles, CheckCircle2, XCircle, Clock, FileText, AlertCircle } from 'lucide-react';
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
        <div className={`rounded-2xl overflow-hidden shadow-xl border-2 ${
            isSuccess 
                ? 'bg-gradient-to-br from-violet-50 via-purple-50 to-fuchsia-50 border-violet-200' 
                : 'bg-gradient-to-br from-red-50 via-rose-50 to-pink-50 border-red-200'
        }`}>
            {/* Header */}
            <div className={`px-5 py-4 ${
                isSuccess 
                    ? 'bg-gradient-to-r from-violet-500 to-purple-500' 
                    : 'bg-gradient-to-r from-red-500 to-rose-500'
            }`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm">
                            {isSuccess ? (
                                <Sparkles className="w-6 h-6 text-white" />
                            ) : (
                                <AlertCircle className="w-6 h-6 text-white" />
                            )}
                        </div>
                        <div>
                            <h3 className="text-white font-bold text-lg">
                                {isSuccess ? '任务完成' : '任务失败'}
                            </h3>
                            {totalIterations && (
                                <div className="flex items-center gap-1 text-white/80 text-sm">
                                    <Clock className="w-3 h-3" />
                                    <span>共 {totalIterations} 次迭代</span>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
                        isSuccess ? 'bg-emerald-400/30 text-emerald-100' : 'bg-red-400/30 text-red-100'
                    }`}>
                        {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                        <span className="text-sm font-medium">{isSuccess ? 'Success' : 'Failed'}</span>
                    </div>
                </div>
            </div>
            
            {/* Content */}
            <div className="p-5">
                {typeof finalContent === 'string' ? (
                    <div className="prose prose-slate max-w-none">
                        <ReactMarkdown
                            components={{
                                p: ({ children }) => <p className="text-slate-700 leading-relaxed mb-4 last:mb-0">{children}</p>,
                                h1: ({ children }) => <h1 className="text-xl font-bold text-slate-800 mb-3">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-lg font-bold text-slate-800 mb-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-base font-bold text-slate-800 mb-2">{children}</h3>,
                                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-4 text-slate-700">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-4 text-slate-700">{children}</ol>,
                                li: ({ children }) => <li className="text-slate-700">{children}</li>,
                                strong: ({ children }) => <strong className="font-bold text-violet-700">{children}</strong>,
                                em: ({ children }) => <em className="text-slate-600 italic">{children}</em>,
                                code: ({ children }) => (
                                    <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono text-violet-600">
                                        {children}
                                    </code>
                                ),
                                pre: ({ children }) => (
                                    <pre className="bg-slate-800 text-slate-200 p-4 rounded-xl overflow-x-auto my-4 font-mono text-sm">
                                        {children}
                                    </pre>
                                ),
                                blockquote: ({ children }) => (
                                    <blockquote className="border-l-4 border-violet-300 pl-4 py-2 my-4 bg-violet-50/50 rounded-r-lg italic text-slate-600">
                                        {children}
                                    </blockquote>
                                ),
                            }}
                        >
                            {finalContent}
                        </ReactMarkdown>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {typeof finalContent === 'object' && finalContent !== null ? (
                            Object.entries(finalContent).map(([key, value]) => (
                                <div key={key} className="flex items-start gap-3 p-3 bg-white/60 rounded-xl">
                                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-100 text-violet-600 flex-shrink-0">
                                        <FileText className="w-4 h-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <span className="text-sm font-medium text-violet-700 block mb-1">{key}</span>
                                        <span className="text-slate-700 break-words">
                                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                        </span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-slate-700">{String(finalContent)}</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ResultItem;
