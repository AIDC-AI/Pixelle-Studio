'use client';

import { useState } from 'react';
import { CheckCircle, XCircle, ChevronDown, ChevronRight, Terminal, AlertTriangle } from 'lucide-react';
import { ExecutionResult } from '@/types/message';

interface IProps {
    result: ExecutionResult;
    executionCount?: number;
}

const ExecutionResultItem: React.FC<IProps> = (props) => {
    const { result, executionCount = 1 } = props;
    const [showDetails, setShowDetails] = useState(false);
    
    const isSuccess = result.status === 'success';
    const hasStderr = result.stderr && result.stderr.trim().length > 0;
    const hasStdout = result.stdout && result.stdout.trim().length > 0;

    return (
        <div className={`rounded-xl overflow-hidden shadow-md border ${
            isSuccess 
                ? 'bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200' 
                : 'bg-gradient-to-br from-red-50 to-orange-50 border-red-200'
        }`}>
            {/* Header */}
            <div 
                className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-colors ${
                    isSuccess ? 'hover:bg-emerald-100/50' : 'hover:bg-red-100/50'
                }`}
                onClick={() => setShowDetails(!showDetails)}
            >
                <div className="flex items-center gap-3">
                    <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${
                        isSuccess ? 'bg-emerald-500/20 text-emerald-600' : 'bg-red-500/20 text-red-600'
                    }`}>
                        {isSuccess ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className={`font-medium ${isSuccess ? 'text-emerald-800' : 'text-red-800'}`}>
                                执行结果 #{executionCount}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                                isSuccess 
                                    ? 'bg-emerald-200/60 text-emerald-700' 
                                    : 'bg-red-200/60 text-red-700'
                            }`}>
                                {isSuccess ? '成功' : '失败'}
                            </span>
                            {hasStderr && isSuccess && (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-200/60 text-amber-700 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" />
                                    有警告
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className={`${isSuccess ? 'text-emerald-600' : 'text-red-600'}`}>
                    {showDetails ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                </div>
            </div>
            
            {/* Details */}
            <div className={`transition-all duration-300 ease-in-out ${showDetails ? 'max-h-[800px]' : 'max-h-0'} overflow-hidden`}>
                <div className="p-4 space-y-4 border-t border-gray-200/50">
                    {/* Stdout */}
                    {hasStdout && (
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <Terminal className="w-4 h-4 text-slate-600" />
                                <span className="text-sm font-medium text-slate-700">输出</span>
                            </div>
                            <pre className="bg-white/80 rounded-lg p-3 text-sm text-slate-700 font-mono overflow-x-auto whitespace-pre-wrap border border-slate-200">
                                {result.stdout}
                            </pre>
                        </div>
                    )}
                    
                    {/* Stderr */}
                    {hasStderr && (
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="w-4 h-4 text-amber-600" />
                                <span className="text-sm font-medium text-amber-700">错误/警告</span>
                            </div>
                            <pre className="bg-amber-50/80 rounded-lg p-3 text-sm text-amber-800 font-mono overflow-x-auto whitespace-pre-wrap border border-amber-200">
                                {result.stderr}
                            </pre>
                        </div>
                    )}
                    
                    {/* Parsed Result */}
                    {result.result && (
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <CheckCircle className="w-4 h-4 text-emerald-600" />
                                <span className="text-sm font-medium text-emerald-700">解析结果</span>
                            </div>
                            <div className="bg-white/80 rounded-lg p-3 border border-emerald-200">
                                <pre className="text-sm text-slate-700 font-mono overflow-x-auto whitespace-pre-wrap">
                                    {typeof result.result === 'string' 
                                        ? result.result 
                                        : JSON.stringify(result.result, null, 2)}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
            </div>
            
            {/* Quick Preview when collapsed */}
            {!showDetails && hasStdout && (
                <div className="px-4 py-2 border-t border-gray-200/30">
                    <p className="text-xs text-slate-500 font-mono line-clamp-1">
                        {result.stdout.split('\n')[0]}...
                    </p>
                </div>
            )}
        </div>
    );
};

export default ExecutionResultItem;

