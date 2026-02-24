// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
        if (isStart) return <RefreshCw className="w-3 h-3 animate-spin" />;
        if (isSuccess) return <CheckCircle className="w-3 h-3" />;
        if (isFailed) return <XCircle className="w-3 h-3" />;
        return <RotateCw className="w-3 h-3" />;
    };

    const getStyles = () => {
        if (isStart) return 'bg-gray-100 border-gray-200 text-gray-600';
        if (isSuccess) return 'bg-green-50 border-green-200 text-green-700';
        if (isFailed) return 'bg-red-50 border-red-200 text-red-700';
        return 'bg-gray-100 border-gray-200 text-gray-600';
    };

    return (
        <div 
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border ${getStyles()}`}
            style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.06)' }}
        >
            {getIcon()}
            <span>
                {isStart ? 'Start' : isSuccess ? 'Done' : isFailed ? 'Failed' : 'Iteration'} 
                {iterNum && ` #${iterNum}`}
            </span>
        </div>
    );
};

export default IterationItem;
