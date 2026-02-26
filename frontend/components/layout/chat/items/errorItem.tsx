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

import { AlertTriangle, XCircle, Settings } from 'lucide-react';

interface IProps {
    content?: string;
    onOpenSettings?: () => void;
}

const ErrorItem: React.FC<IProps> = (props) => {
    const { content = '', onOpenSettings } = props;

    // Detect API-key-missing message so we can show a helpful action button
    const isApiKeyMissing = content.includes('API Key') && content.includes('Settings');

    return (
        <div 
            className={`flex items-start gap-2 p-3 border rounded-lg ${
                isApiKeyMissing 
                    ? 'bg-amber-50 border-amber-300' 
                    : 'bg-red-50 border-red-200'
            }`}
            style={{ boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.08)' }}
        >
            <div className={`flex items-center justify-center w-6 h-6 rounded shrink-0 ${
                isApiKeyMissing ? 'bg-amber-100 text-amber-600' : 'bg-red-100 text-red-600'
            }`}>
                {isApiKeyMissing ? <Settings className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-xs font-medium ${isApiKeyMissing ? 'text-amber-700' : 'text-red-700'}`}>
                        {isApiKeyMissing ? 'Configuration Required' : 'Error'}
                    </span>
                    <AlertTriangle className={`w-3 h-3 ${isApiKeyMissing ? 'text-amber-500' : 'text-red-500'}`} />
                </div>
                <p className={`text-xs whitespace-pre-wrap break-words ${isApiKeyMissing ? 'text-amber-700' : 'text-red-600'}`}>
                    {content}
                </p>
                {isApiKeyMissing && onOpenSettings && (
                    <button
                        onClick={onOpenSettings}
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-md transition-colors"
                    >
                        <Settings className="w-3 h-3" />
                        Open Settings
                    </button>
                )}
            </div>
        </div>
    );
};

export default ErrorItem;
