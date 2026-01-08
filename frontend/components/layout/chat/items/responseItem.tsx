'use client';

import { Bot, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface IProps {
    content: string;
}

const ResponseItem: React.FC<IProps> = (props) => {
    const { content } = props;

    return (
        <div className="flex gap-3">
            {/* Avatar */}
            <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                    <Bot className="w-5 h-5 text-white" />
                </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="bg-white rounded-2xl rounded-tl-sm shadow-sm border border-slate-100 px-4 py-3">
                    <div className="prose prose-slate max-w-none prose-sm">
                        <ReactMarkdown
                            components={{
                                p: ({ children }) => <p className="text-slate-700 leading-relaxed mb-3 last:mb-0">{children}</p>,
                                h1: ({ children }) => <h1 className="text-lg font-bold text-slate-800 mb-2">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-base font-bold text-slate-800 mb-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-sm font-bold text-slate-800 mb-2">{children}</h3>,
                                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3 text-slate-700">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3 text-slate-700">{children}</ol>,
                                li: ({ children }) => <li className="text-slate-700">{children}</li>,
                                strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
                                em: ({ children }) => <em className="text-slate-600 italic">{children}</em>,
                                code: ({ children }) => (
                                    <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono text-indigo-600">
                                        {children}
                                    </code>
                                ),
                                pre: ({ children }) => (
                                    <pre className="bg-slate-800 text-slate-200 p-3 rounded-xl overflow-x-auto my-3 font-mono text-xs">
                                        {children}
                                    </pre>
                                ),
                                blockquote: ({ children }) => (
                                    <blockquote className="border-l-3 border-indigo-300 pl-3 py-1 my-3 bg-indigo-50/50 rounded-r-lg italic text-slate-600 text-sm">
                                        {children}
                                    </blockquote>
                                ),
                            }}
                        >
                            {content}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResponseItem;

