/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use client';

import { Terminal } from 'lucide-react';

interface IProps {
    content?: string;
}

const LogItem: React.FC<IProps> = (props) => {
    const { content = '' } = props;

    // Parse log type from content (e.g., "[stdout] message" or "[stderr] message")
    const isStderr = content.toLowerCase().includes('[stderr]');
    const cleanContent = content.replace(/^\[(stdout|stderr|LOG)\]\s*/i, '');

    return (
        <div 
            className={`flex items-start gap-2 px-3 py-1.5 rounded font-mono text-xs ${
                isStderr 
                    ? 'bg-amber-50 border border-amber-200' 
                    : 'bg-gray-100 border border-gray-200'
            }`}
            style={{ boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.06)' }}
        >
            <Terminal className={`w-3 h-3 mt-0.5 flex-shrink-0 ${
                isStderr ? 'text-amber-500' : 'text-gray-400'
            }`} />
            <span className={isStderr ? 'text-amber-700' : 'text-gray-600'}>
                {cleanContent}
            </span>
        </div>
    );
};

export default LogItem;
