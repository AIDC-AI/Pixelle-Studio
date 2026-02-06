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

import { Settings, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Message } from '@/types/message';

interface IProps {
    children: React.ReactNode;
    isComplete?: boolean;
}

const SystemOperationGroup: React.FC<IProps> = ({ children, isComplete = false }) => {
    const [isExpanded, setIsExpanded] = useState(true);

    return (
        <div 
            className="bg-gray-100 rounded-lg border border-gray-200 overflow-hidden"
            style={{ boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.06)' }}
        >
            {/* Header */}
            <div 
                className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-5 h-5 rounded bg-gray-400 text-white">
                        <Settings className="w-3 h-3" />
                    </div>
                    <span className="text-xs font-medium text-gray-600">
                        System Process 
                    </span>
                    {isComplete && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                            已完成
                        </span>
                    )}
                </div>
                <div className="text-gray-500">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
            </div>
            
            {/* Content */}
            <div className={`transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-none' : 'max-h-0'} overflow-auto`}>
                <div className="p-3 space-y-2">
                    {children}
                </div>
            </div>
        </div>
    );
};

export default SystemOperationGroup;




