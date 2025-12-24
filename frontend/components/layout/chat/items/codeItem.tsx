'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Code2, Copy, Check } from 'lucide-react';

interface IProps {
    code: string;
    executionCount?: number;
    reasoning?: string;
}

const CodeItem: React.FC<IProps> = (props) => {
    const { code, executionCount = 1, reasoning } = props;
    const [isExpanded, setIsExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const lineCount = code.split('\n').length;

    return (
        <div className="bg-linear-to-br from-slate-900 to-slate-800 rounded-xl overflow-hidden shadow-lg border border-slate-700/50">
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
                <div className="relative">
                    {/* Line numbers + Code */}
                    <div className="flex overflow-auto max-h-[500px]">
                        {/* Line numbers */}
                        <div className="shrink-0 py-4 px-3 bg-slate-900/50 text-right select-none border-r border-slate-700/50">
                            {code.split('\n').map((_, idx) => (
                                <div key={idx} className="text-slate-600 text-xs leading-6 font-mono">
                                    {idx + 1}
                                </div>
                            ))}
                        </div>
                        {/* Code */}
                        <pre className="flex-1 py-4 px-4 text-slate-200 text-sm font-mono overflow-x-auto">
                            <code>
                                {code.split('\n').map((line, idx) => (
                                    <div key={idx} className="leading-6 hover:bg-slate-700/30 -mx-4 px-4">
                                        {highlightPythonLine(line)}
                                    </div>
                                ))}
                            </code>
                        </pre>
                    </div>
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

// Simple Python syntax highlighting
function highlightPythonLine(line: string): React.ReactNode {
    const keywords = ['import', 'from', 'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'return', 'try', 'except', 'with', 'as', 'in', 'not', 'and', 'or', 'True', 'False', 'None', 'async', 'await', 'print', 'raise'];
    const builtins = ['str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'bool', 'len', 'range', 'open', 'json', 'Path'];
    
    // Handle comments
    if (line.trim().startsWith('#')) {
        return <span className="text-slate-500 italic">{line}</span>;
    }
    
    // Handle strings
    if (line.includes('"') || line.includes("'")) {
        const stringRegex = /(["'])((?:\\.|[^\\])*?)\1/g;
        const parts = [];
        let lastIndex = 0;
        let match;
        
        while ((match = stringRegex.exec(line)) !== null) {
            if (match.index > lastIndex) {
                parts.push(highlightKeywords(line.slice(lastIndex, match.index), keywords, builtins));
            }
            parts.push(<span key={match.index} className="text-amber-400">{match[0]}</span>);
            lastIndex = match.index + match[0].length;
        }
        
        if (lastIndex < line.length) {
            parts.push(highlightKeywords(line.slice(lastIndex), keywords, builtins));
        }
        
        return <>{parts}</>;
    }
    
    return highlightKeywords(line, keywords, builtins);
}

function highlightKeywords(text: string, keywords: string[], builtins: string[]): React.ReactNode {
    const parts = text.split(/(\s+)/);
    return (
        <div key={text}>
            {parts.map((part, idx) => {
                if (keywords.includes(part)) {
                    return <span key={idx} className="text-pink-400 font-medium">{part}</span>;
                }
                if (builtins.includes(part)) {
                    return <span key={idx} className="text-cyan-400">{part}</span>;
                }
                // Numbers
                if (/^\d+(\.\d+)?$/.test(part)) {
                    return <span key={idx} className="text-orange-400">{part}</span>;
                }
                return <span key={idx}>part</span>;
            })}
        </div>
    );
}

export default CodeItem;

