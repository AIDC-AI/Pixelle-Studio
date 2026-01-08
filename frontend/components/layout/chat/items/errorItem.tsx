'use client';

import { AlertTriangle, XCircle } from 'lucide-react';

interface IProps {
    content?: string;
}

const ErrorItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    return (
        <div 
            className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg"
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.08)' }}
        >
            <div className="flex items-center justify-center w-6 h-6 rounded bg-red-100 text-red-600 flex-shrink-0">
                <XCircle className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-xs font-medium text-red-700">错误</span>
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                </div>
                <p className="text-red-600 text-xs whitespace-pre-wrap break-words">
                    {content}
                </p>
            </div>
        </div>
    );
};

export default ErrorItem;
