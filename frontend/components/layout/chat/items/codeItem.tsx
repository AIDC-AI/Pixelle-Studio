'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Code2, Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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

    // 自定义样式，与现有设计保持一致
    const customStyle = {
        margin: 0,
        padding: '1rem',
        background: 'transparent',
        fontSize: '0.875rem',
        lineHeight: '1.5rem',
    };

    return (
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl overflow-hidden shadow-lg border border-slate-700/50">
            {/* Header */}
            <div 
                className="flex items-center justify-between px-4 py-3 bg-slate-800/50 cursor-pointer hover:bg-slate-800/80 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400">
                        <Code2 className="w-4 h-4" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-slate-200 font-medium">
                                执行代码 #{executionCount}
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
                                {lineCount} 行
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">
                                {language}
                            </span>
                        </div>
                        {reasoning && (
                            <p className="text-xs text-slate-400 mt-1 max-w-md truncate">
                                💡 {reasoning}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleCopy();
                        }}
                        className="p-2 rounded-lg hover:bg-slate-700 transition-colors text-slate-400 hover:text-slate-200"
                        title="复制代码"
                    >
                        {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <div className="text-slate-400">
                        {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </div>
                </div>
            </div>
            
            {/* Code Content */}
            <div className={`transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[600px]' : 'max-h-0'} overflow-hidden`}>
                <div className="relative overflow-auto max-h-[500px]">
                    <SyntaxHighlighter
                        language={language}
                        style={vscDarkPlus}
                        customStyle={customStyle}
                        showLineNumbers
                        lineNumberStyle={{
                            minWidth: '3em',
                            paddingRight: '1em',
                            color: '#475569',
                            userSelect: 'none',
                        }}
                        wrapLines
                        lineProps={(lineNumber) => ({
                            style: {
                                display: 'block',
                                cursor: 'pointer',
                            },
                            onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
                                e.currentTarget.style.backgroundColor = 'rgba(51, 65, 85, 0.3)';
                            },
                            onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
                                e.currentTarget.style.backgroundColor = 'transparent';
                            },
                        })}
                    >
                        {code}
                    </SyntaxHighlighter>
                </div>
            </div>
            
            {/* Collapsed preview */}
            {!isExpanded && (
                <div className="px-4 py-2 border-t border-slate-700/50">
                    <code className="text-slate-400 text-xs font-mono line-clamp-2">
                        {code.split('\n').slice(0, 2).join('\n')}
                        {lineCount > 2 && '...'}
                    </code>
                </div>
            )}
        </div>
    );
};

export default CodeItem;

