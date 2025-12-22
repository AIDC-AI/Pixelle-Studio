'use client';

import { ClipboardCheck, ChevronDown, ChevronRight, CheckCircle, AlertCircle } from 'lucide-react';
import { useState } from 'react';

interface IProps {
    content?: string;
}

const EvalutaionItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;
    const [isExpanded, setIsExpanded] = useState(false);

    // Parse evaluation result
    const isPassing = content.toLowerCase().includes('pass');
    const confidenceMatch = content.match(/(\d+)%/);
    const confidence = confidenceMatch ? parseInt(confidenceMatch[1]) : null;

    // Extract reason
    const reasonMatch = content.match(/Reason:\s*(.+)$/s);
    const reason = reasonMatch ? reasonMatch[1].trim() : content;

    return (
        <div className={`rounded-xl overflow-hidden border ${
            isPassing 
                ? 'bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200'
                : 'bg-gradient-to-br from-amber-50 to-orange-50 border-amber-200'
        }`}>
            {/* Header */}
            <div 
                className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-colors ${
                    isPassing ? 'hover:bg-emerald-100/50' : 'hover:bg-amber-100/50'
                }`}
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${
                        isPassing ? 'bg-emerald-200/60 text-emerald-600' : 'bg-amber-200/60 text-amber-600'
                    }`}>
                        {isPassing ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className={`font-medium ${isPassing ? 'text-emerald-800' : 'text-amber-800'}`}>
                            评估结果
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            isPassing 
                                ? 'bg-emerald-200/60 text-emerald-700' 
                                : 'bg-amber-200/60 text-amber-700'
                        }`}>
                            {isPassing ? '通过' : '需改进'}
                        </span>
                        {confidence !== null && (
                            <span className={`text-xs ${isPassing ? 'text-emerald-600' : 'text-amber-600'}`}>
                                置信度 {confidence}%
                            </span>
                        )}
                    </div>
                </div>
                <div className={isPassing ? 'text-emerald-600' : 'text-amber-600'}>
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content */}
            {isExpanded && (
                <div className="px-4 pb-4">
                    <div className={`rounded-lg p-3 border ${
                        isPassing ? 'bg-white/60 border-emerald-100' : 'bg-white/60 border-amber-100'
                    }`}>
                        <div className="flex items-start gap-2 mb-2">
                            <ClipboardCheck className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                                isPassing ? 'text-emerald-500' : 'text-amber-500'
                            }`} />
                            <span className={`text-sm font-medium ${
                                isPassing ? 'text-emerald-700' : 'text-amber-700'
                            }`}>
                                评估原因
                            </span>
                        </div>
                        <p className={`text-sm leading-relaxed ${
                            isPassing ? 'text-emerald-800' : 'text-amber-800'
                        }`}>
                            {reason}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EvalutaionItem;
