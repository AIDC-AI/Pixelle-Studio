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

import { Loader2, Settings, Info, CheckCircle } from 'lucide-react';

interface IProps {
    content?: string;
    isLast?: boolean
}

const SystemItem: React.FC<IProps> = (props) => {
    const { content = '', isLast } = props;

    // Determine the icon and style based on content
    const isProcessing = content.toLowerCase().includes('processing') || 
                         content.toLowerCase().includes('executing') ||
                         content.toLowerCase().includes('loading');
    const isComplete = content.toLowerCase().includes('complete') ||
                       content.toLowerCase().includes('success') ||
                       content.toLowerCase().includes('done');

    if (isProcessing && !isLast) 
        return null
    
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
