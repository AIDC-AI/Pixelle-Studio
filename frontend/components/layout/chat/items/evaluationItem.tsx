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
        <div 
            className="rounded-lg overflow-hidden border bg-gray-100 border-gray-200"
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)' }}
        >
            {/* Header */}
            <div 
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-150 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2">
                    <div className={`flex items-center justify-center w-6 h-6 rounded ${
                        isPassing ? 'bg-green-100 text-green-600' : 'bg-amber-100 text-amber-600'
                    }`}>
                        {isPassing ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-gray-600">
                            Evaluation Result
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                            isPassing 
                                ? 'bg-green-100 text-green-700' 
                                : 'bg-amber-100 text-amber-700'
                        }`}>
                            {isPassing ? 'Pass' : 'Needs Improvement'}
                        </span>
                        {confidence !== null && (
                            <span className="text-xs text-gray-500">
                                Confidence {confidence}%
                            </span>
                        )}
                    </div>
                </div>
                <div className="text-gray-500">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content */}
            {isExpanded && (
                <div className="px-3 pb-3">
                    <div className="rounded p-2 border bg-white border-gray-200">
                        <div className="flex items-start gap-1.5 mb-1">
                            <ClipboardCheck className={`w-3 h-3 mt-0.5 shrink-0 ${
                                isPassing ? 'text-green-500' : 'text-amber-500'
                            }`} />
                            <span className="text-xs font-medium text-gray-600">
                                Evaluation Reason
                            </span>
                        </div>
                        <p className="text-xs leading-relaxed text-gray-700">
                            {reason}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EvalutaionItem;
