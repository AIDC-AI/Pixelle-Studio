'use client';

import { useState } from 'react';
import { CheckCircle, XCircle, ChevronDown, ChevronRight, Terminal, AlertTriangle } from 'lucide-react';
import { ExecutionResult } from '@/types/message';
import CodeHighlighter from '@/components/ui/codeHighlighter';

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
    const resultString = !!result.result ? (typeof result.result === 'string' 
                                        ? result.result  
                                        : JSON.stringify(result.result, null, 2)) : null
                                        
    return (
        <div className={`rounded-lg overflow-hidden border ${
            isSuccess 
                ? 'bg-white border-teal-200' 
                : 'bg-white border-red-200'
        }`}>
            {/* Header - 深绿色调 */}
            <div 
                className={`flex items-center justify-between px-3 py-2 cursor-pointer transition-colors ${
                    isSuccess 
                        ? 'bg-teal-50 hover:bg-teal-100 border-b border-teal-200' 
                        : 'bg-red-50 hover:bg-red-100 border-b border-red-200'
                }`}
                onClick={() => setShowDetails(!showDetails)}
            >
                <div className="flex items-center gap-2">
                    <div className={`flex items-center justify-center w-5 h-5 rounded ${
                        isSuccess ? 'bg-teal-500 text-white' : 'bg-red-500 text-white'
                    }`}>
                        {isSuccess ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className={`text-xs font-medium ${isSuccess ? 'text-teal-700' : 'text-red-700'}`}>
                            Return #{executionCount}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                            isSuccess 
                                ? 'bg-teal-100 text-teal-700' 
                                : 'bg-red-100 text-red-700'
                        }`}>
                            {isSuccess ? '成功' : '失败'}
                        </span>
                        {hasStderr && isSuccess && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 flex items-center gap-0.5">
                                <AlertTriangle className="w-2.5 h-2.5" />
                                警告
                            </span>
                        )}
                    </div>
                </div>
                <div className={isSuccess ? 'text-teal-600' : 'text-red-600'}>
                    {showDetails ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Details */}
            <div className={`transition-all duration-300 ease-in-out ${showDetails ? 'max-h-[600px]' : 'max-h-0'} overflow-hidden`}>
                <div className="p-3 space-y-3 bg-white">
                    {/* Stderr */}
                    {hasStderr && (
                        <div>
                            <div className="flex items-center gap-1.5 mb-1.5">
                                <AlertTriangle className="w-3 h-3 text-amber-600" />
                                <span className="text-xs font-medium text-amber-700">错误/警告</span>
                            </div>
                            <pre className="bg-amber-50 rounded p-2 text-xs text-amber-800 font-mono overflow-x-auto whitespace-pre-wrap border border-amber-200">
                                {result.stderr}
                            </pre>
                        </div>
                    )}
                    
                    {/* Parsed Result or Stdout */}  
                    {resultString ? (
                        <div>
                            <div className="flex items-center gap-1.5 mb-1.5">
                                <CheckCircle className="w-3 h-3 text-teal-600" />
                                <span className="text-xs font-medium text-teal-700">解析结果</span>
                            </div>
                            <CodeHighlighter 
                                language={"json"}
                                code={resultString}
                            />
                            {/* <div className="bg-teal-50 rounded p-2 border border-teal-200">
                                <pre className="text-xs text-gray-700 font-mono overflow-x-auto whitespace-pre-wrap">
                                    {typeof result.result === 'string' 
                                        ? result.result  
                                        : JSON.stringify(result.result, null, 2)}
                                </pre>
                            </div> */}
                        </div>
                    ) : (hasStdout && (
                        <div>
                            <div className="flex items-center gap-1.5 mb-1.5">
                                <Terminal className="w-3 h-3 text-gray-500" />
                                <span className="text-xs font-medium text-gray-600">输出</span>
                            </div>
                            <pre className="bg-gray-50 rounded p-2 text-xs text-gray-700 font-mono overflow-x-auto whitespace-pre-wrap border border-gray-200">
                                {result.stdout}
                            </pre>
                        </div>
                    ))}
                </div>
            </div>
            
            {/* Quick Preview when collapsed */}
            {!showDetails && resultString && (
                <div className="px-3 py-1.5 bg-gray-50">
                    <p className="text-xs text-gray-500 font-mono">
                        {resultString}
                    </p>
                </div>
            )}
        </div>
    );
};

export default ExecutionResultItem;
