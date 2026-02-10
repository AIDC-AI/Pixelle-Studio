import { Check, Copy, ExternalLink } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import CodeHighlighter from "./codeHighlighter";

interface IProps {
    content: string;
    codeColor?: string
}

const MarkDown: React.FC<IProps> = (props) => {
    const { content, codeColor = 'text-red-600' } = props;
    const [copiedCode, setCopiedCode] = useState<string | null>(null);

    const handleCopyCode = async (code: string) => {
        await navigator.clipboard.writeText(code);
        setCopiedCode(code);
        setTimeout(() => setCopiedCode(null), 2000);
    };

    return <ReactMarkdown
        components={{
            // Use div instead of p tag wrapper
            p: ({ children }) => <div className="text-gray-700 leading-relaxed mb-3 last:mb-0">{children}</div>,
            h1: ({ children }) => <h1 className="text-lg font-bold text-gray-800 mb-2">{children}</h1>,
            h2: ({ children }) => <h2 className="text-base font-bold text-gray-800 mb-2">{children}</h2>,
            h3: ({ children }) => <h3 className="text-sm font-bold text-gray-800 mb-2">{children}</h3>,
            ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3 text-gray-700">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3 text-gray-700">{children}</ol>,
            li: ({ children }) => <li className="text-gray-700">{children}</li>,
            a: ({ href, children }) => (
                <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-orange-600 hover:text-orange-700 hover:underline transition-colors"
                >
                    {children}
                    <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
            ),
            strong: ({ children }) => <strong className="font-bold text-gray-800">{children}</strong>,
            em: ({ children }) => <em className="text-gray-600 italic">{children}</em>,
            code: ({ node, inline, className, children, ...props }: any) => {
                const match = /language-(\w+)/.exec(className || '');
                const codeString = String(children).replace(/\n$/, '');
                
                if (inline) {
                    // Inline code
                    return (
                        <code className={`bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono ${codeColor}`} {...props}>
                            {children}
                        </code>
                    );
                }
                
                const language = !!match ? match?.[1] : "python"
                // Code block
                return (
                    <div className="relative group my-3">
                        <div className="absolute right-2 top-2 z-10">
                            <button
                                onClick={() => handleCopyCode(codeString)}
                                className="p-1.5 rounded-md bg-gray-700 hover:bg-gray-600 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Copy code"
                            >
                                {copiedCode === codeString ? (
                                    <Check className="w-3.5 h-3.5" />
                                ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                )}
                            </button>
                        </div>
                        <CodeHighlighter 
                            language={language}
                            code={codeString}
                        />
                    </div>
                );                          
            },
            pre: ({ children }) => <>{children}</>,
            blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-3 bg-blue-50 rounded-r-lg italic text-gray-700 text-sm">
                    {children}
                </blockquote>
            ),
        }}
    >
        {content}
    </ReactMarkdown>
}

export default MarkDown;