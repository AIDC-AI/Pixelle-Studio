'use client';

import { Bot, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface IProps {
    content: string;
}

const ResponseItem: React.FC<IProps> = (props) => {
    const { content } = props;
    const [copiedCode, setCopiedCode] = useState<string | null>(null);

    const handleCopyCode = async (code: string) => {
        await navigator.clipboard.writeText(code);
        setCopiedCode(code);
        setTimeout(() => setCopiedCode(null), 2000);
    };

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
                                code: ({ node, inline, className, children, ...props }: any) => {
                                    const match = /language-(\w+)/.exec(className || '');
                                    const codeString = String(children).replace(/\n$/, '');
                                    
                                    // 代码块（有语言标识）
                                    if (!inline && match) {
                                        const language = match[1];
                                        return (
                                            <div className="relative group my-3">
                                                <div className="absolute right-2 top-2 z-10">
                                                    <button
                                                        onClick={() => handleCopyCode(codeString)}
                                                        className="p-1.5 rounded-md bg-gray-700 hover:bg-gray-600 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity"
                                                        title="复制代码"
                                                    >
                                                        {copiedCode === codeString ? (
                                                            <Check className="w-3.5 h-3.5" />
                                                        ) : (
                                                            <Copy className="w-3.5 h-3.5" />
                                                        )}
                                                    </button>
                                                </div>
                                                <SyntaxHighlighter
                                                    language={language}
                                                    style={vscDarkPlus}
                                                    customStyle={{
                                                        margin: 0,
                                                        borderRadius: '0.5rem',
                                                        fontSize: '0.8rem',
                                                        lineHeight: '1.5',
                                                    }}
                                                    showLineNumbers
                                                    lineNumberStyle={{
                                                        minWidth: '2.5em',
                                                        paddingRight: '1em',
                                                        color: '#6e7681',
                                                        userSelect: 'none',
                                                        fontSize: '0.75rem',
                                                    }}
                                                    wrapLongLines
                                                >
                                                    {codeString}
                                                </SyntaxHighlighter>
                                            </div>
                                        );
                                    }
                                    
                                    // 代码块（无语言标识，使用通用格式）
                                    if (!inline) {
                                        return (
                                            <div className="relative group my-3">
                                                <div className="absolute right-2 top-2 z-10">
                                                    <button
                                                        onClick={() => handleCopyCode(codeString)}
                                                        className="p-1.5 rounded-md bg-gray-700 hover:bg-gray-600 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity"
                                                        title="复制代码"
                                                    >
                                                        {copiedCode === codeString ? (
                                                            <Check className="w-3.5 h-3.5" />
                                                        ) : (
                                                            <Copy className="w-3.5 h-3.5" />
                                                        )}
                                                    </button>
                                                </div>
                                                <SyntaxHighlighter
                                                    language="python"
                                                    style={vscDarkPlus}
                                                    customStyle={{
                                                        margin: 0,
                                                        borderRadius: '0.5rem',
                                                        fontSize: '0.8rem',
                                                        lineHeight: '1.5',
                                                    }}
                                                    showLineNumbers
                                                    lineNumberStyle={{
                                                        minWidth: '2.5em',
                                                        paddingRight: '1em',
                                                        color: '#6e7681',
                                                        userSelect: 'none',
                                                        fontSize: '0.75rem',
                                                    }}
                                                    wrapLongLines
                                                >
                                                    {codeString}
                                                </SyntaxHighlighter>
                                            </div>
                                        );
                                    }
                                    
                                    // 行内代码
                                    return (
                                        <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-red-600" {...props}>
                                            {children}
                                        </code>
                                    );
                                },
                                pre: ({ children }) => <div>{children}</div>,
                                blockquote: ({ children }) => (
                                    <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-3 bg-blue-50 rounded-r-lg italic text-gray-700 text-sm">
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
