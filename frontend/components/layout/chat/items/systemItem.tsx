'use client';

import { Loader2, Settings, Info, CheckCircle } from 'lucide-react';

interface IProps {
    content?: string;
}

const SystemItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    // Determine the icon and style based on content
    const isProcessing = content.toLowerCase().includes('processing') || 
                         content.toLowerCase().includes('executing') ||
                         content.toLowerCase().includes('loading');
    const isComplete = content.toLowerCase().includes('complete') ||
                       content.toLowerCase().includes('success') ||
                       content.toLowerCase().includes('done');

    return (
        <div className="flex items-center gap-2 py-2">
            <div className={`flex items-center justify-center w-6 h-6 rounded-full ${
                isProcessing 
                    ? 'bg-blue-100 text-blue-500' 
                    : isComplete 
                        ? 'bg-emerald-100 text-emerald-500'
                        : 'bg-slate-100 text-slate-500'
            }`}>
                {isProcessing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : isComplete ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                ) : (
                    <Info className="w-3.5 h-3.5" />
                )}
            </div>
            <span className={`text-sm ${
                isProcessing 
                    ? 'text-blue-600' 
                    : isComplete 
                        ? 'text-emerald-600'
                        : 'text-slate-500'
            }`}>
                {content}
            </span>
        </div>
    );
};

export default SystemItem;
