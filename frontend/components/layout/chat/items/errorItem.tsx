'use client';

import { AlertTriangle, XCircle } from 'lucide-react';

interface IProps {
    content?: string;
}

const ErrorItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    return (
        <div className="flex items-start gap-3 p-4 bg-gradient-to-br from-red-50 to-rose-50 border border-red-200 rounded-xl">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-red-100 text-red-600 flex-shrink-0">
                <XCircle className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-red-700">错误</span>
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                </div>
                <p className="text-red-600 text-sm whitespace-pre-wrap break-words">
                    {content}
                </p>
            </div>
        </div>
    );
};

export default ErrorItem;
