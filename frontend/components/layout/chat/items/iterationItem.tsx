'use client';

import { RefreshCw, CheckCircle, XCircle, RotateCw } from 'lucide-react';

interface IProps {
    content?: string;
}

const IterationItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    // Parse iteration status
    const isStart = content.toLowerCase().includes('starting');
    const isSuccess = content.toLowerCase().includes('success');
    const isFailed = content.toLowerCase().includes('fail');

    // Extract iteration number
    const iterMatch = content.match(/iteration\s*(\d+)/i);
    const iterNum = iterMatch ? iterMatch[1] : '';

    const getIcon = () => {
        if (isStart) return <RefreshCw className="w-3.5 h-3.5 animate-spin" />;
        if (isSuccess) return <CheckCircle className="w-3.5 h-3.5" />;
        if (isFailed) return <XCircle className="w-3.5 h-3.5" />;
        return <RotateCw className="w-3.5 h-3.5" />;
    };

    const getStyles = () => {
        if (isStart) return 'bg-blue-50 border-blue-200 text-blue-700';
        if (isSuccess) return 'bg-emerald-50 border-emerald-200 text-emerald-700';
        if (isFailed) return 'bg-red-50 border-red-200 text-red-700';
        return 'bg-slate-50 border-slate-200 text-slate-700';
    };

    return (
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${getStyles()}`}>
            {getIcon()}
            <span>
                {isStart ? '开始' : isSuccess ? '完成' : isFailed ? '失败' : '迭代'} 
                {iterNum && ` #${iterNum}`}
            </span>
        </div>
    );
};

export default IterationItem;
