'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Code2, Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface IProps {
    code: string;
    language?: string;
    executionCount?: number;
    reasoning?: string;
}

const CodeItem: React.FC<IProps> = (props) => {
    const { code, language = 'python', executionCount = 1, reasoning } = props;
    const [isExpanded, setIsExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const lineCount = code.split('\n').length;

    // 白色底风格
    const customStyle = {
        margin: 0,
        padding: '0.75rem',
        background: '#ffffff',
        fontSize: '0.75rem',
        lineHeight: '1.25rem',
        borderRadius: '0.375rem',
    };

    return (
        <div className="bg-white rounded-lg overflow-hidden border border-emerald-200">
            {/* Header - 浅绿色 */}
            <div 
                className="flex items-center justify-between px-3 py-2 bg-emerald-50 cursor-pointer hover:bg-emerald-100 transition-colors border-b border-emerald-200"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-5 h-5 rounded bg-emerald-500 text-white">
                        <Code2 className="w-3 h-3" />
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-emerald-700 text-xs font-medium">
                            Execute Code #{executionCount}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-600">
                            {lineCount} 行
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleCopy();
                        }}
                        className="p-1 rounded hover:bg-emerald-200 transition-colors text-emerald-600"
                        title="复制代码"
                    >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </button>
                    <div className="text-emerald-600">
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </div>
                </div>
            </div>
            
            {/* Reasoning */}
            {reasoning && (
                <div className="px-3 py-1.5 bg-emerald-50/50 border-b border-emerald-100">
                    <p className="text-xs text-emerald-600 truncate">
                        💡 {reasoning}
                    </p>
                </div>
            )}
            
            {/* Code Content - 白色底 */}
            <div className={`transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[500px]' : 'max-h-0'} overflow-hidden`}>
                <div className="relative overflow-auto max-h-100">
                    <SyntaxHighlighter
                        language={language}
                        style={vs}
                        customStyle={customStyle}
                        showLineNumbers
                        lineNumberStyle={{
                            minWidth: '2.5em',
                            paddingRight: '0.75em',
                            color: '#9ca3af',
                            userSelect: 'none',
                            fontSize: '0.7rem',
                        }}
                        wrapLines
                    >
                        {code}
                    </SyntaxHighlighter>
                </div>
            </div>
            
            {/* Collapsed preview */}
            {!isExpanded && (
                <div className="px-3 py-1.5 bg-gray-50">
                    <code className="text-gray-500 text-xs font-mono line-clamp-1">
                        {code.split('\n')[0]}
                        {lineCount > 1 && '...'}
                    </code>
                </div>
            )}
        </div>
    );
};

export default CodeItem;
