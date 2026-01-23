'use client';

import { Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface IProps {
    content: string;
    isStreaming?: boolean;
}

const ResponseItem: React.FC<IProps> = (props) => {
    const { content } = props;

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
                <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 px-4 py-3">
                    <div className="prose prose-slate max-w-none prose-sm">
                        <ReactMarkdown
                            components={{
                                p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-3 last:mb-0">{children}</p>,
                                h1: ({ children }) => <h1 className="text-lg font-bold text-gray-800 mb-2">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-base font-bold text-gray-800 mb-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-sm font-bold text-gray-800 mb-2">{children}</h3>,
                                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3 text-gray-700">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3 text-gray-700">{children}</ol>,
                                li: ({ children }) => <li className="text-gray-700">{children}</li>,
                                strong: ({ children }) => <strong className="font-semibold text-gray-800">{children}</strong>,
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
                            {content}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResponseItem;
