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

import CodeHighlighter from '@/components/ui/codeHighlighter';
import { Wrench, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useState, useMemo } from 'react';

interface IProps {
    toolCall?: {
        name: string;
        arguments?: Record<string, any>;
        result?: any;
        call_id?: string;
    };
    isResult?: boolean;
}

// Tool names that contain code in their arguments
const CODE_TOOLS: Record<string, { codeField: string; langField?: string; defaultLang: string; pathField?: string }> = {
    shell_exec: { codeField: 'command', langField: 'shell_type', defaultLang: 'bash' },
    exec: { codeField: 'command', defaultLang: 'bash' },
    write_file: { codeField: 'content', defaultLang: 'python', pathField: 'path' },
    edit_file: { codeField: 'new_string', defaultLang: 'python', pathField: 'path' },
};

// Infer language from file extension
const inferLangFromPath = (path: string): string | null => {
    const ext = path.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
        py: 'python', js: 'javascript', ts: 'typescript', tsx: 'tsx', jsx: 'jsx',
        sh: 'bash', bash: 'bash', zsh: 'bash', html: 'html', css: 'css',
        json: 'json', yml: 'yaml', yaml: 'yaml', md: 'markdown', sql: 'sql',
        rb: 'ruby', go: 'go', rs: 'rust', java: 'java', cpp: 'cpp', c: 'c',
        xml: 'xml', toml: 'toml', ini: 'ini', conf: 'bash',
    };
    return ext ? langMap[ext] || null : null;
};

// Parse arguments: backend may send as JSON string or parsed object
const parseArgs = (args: any): Record<string, any> | null => {
    if (!args) return null;
    if (typeof args === 'object' && !Array.isArray(args)) return args;
    if (typeof args === 'string') {
        try { return JSON.parse(args); } catch { return null; }
    }
    return null;
};

const ToolCallItem: React.FC<IProps> = ({ toolCall, isResult = false }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!toolCall) return null;

    // Parse arguments once (handles both string and object formats)
    const parsedArgs = useMemo(() => parseArgs(toolCall.arguments), [toolCall.arguments]);
    const hasArguments = parsedArgs !== null && Object.keys(parsedArgs).length > 0;
    const hasResult = toolCall.result !== undefined;

    // Format JSON string, handle possible parsing errors
    const formatJson = (data: any): string => {
        if (typeof data === 'string') {
            try {
                const parsed = JSON.parse(data);
                return JSON.stringify(parsed, null, 2);
            } catch {
                return data;
            }
        }
        return JSON.stringify(data, null, 2);
    };

    // Parse smart rendering info for code-bearing tools
    const codeRenderInfo = useMemo(() => {
        if (isResult || !hasArguments || !parsedArgs) return null;
        const config = CODE_TOOLS[toolCall.name];
        if (!config) return null;

        const codeContent = parsedArgs[config.codeField];
        if (!codeContent || typeof codeContent !== 'string') return null;

        // Determine language
        let lang = config.defaultLang;
        if (config.langField && parsedArgs[config.langField]) {
            lang = parsedArgs[config.langField];
        }
        if (config.pathField && parsedArgs[config.pathField]) {
            const inferred = inferLangFromPath(parsedArgs[config.pathField]);
            if (inferred) lang = inferred;
        }

        // Collect remaining args (non-code fields)
        const restArgs: Record<string, any> = {};
        for (const [k, v] of Object.entries(parsedArgs)) {
            if (k !== config.codeField) restArgs[k] = v;
        }

        return { code: codeContent, language: lang, restArgs };
    }, [toolCall, isResult, hasArguments, parsedArgs]);

    // Render plain JSON code block
    const renderJsonBlock = (code: string, title: string) => (
        <div className="bg-gray-50 rounded p-2">
            <div className="text-xs font-medium text-gray-600 mb-1">{title}:</div>
            <CodeHighlighter 
                language="json"
                code={code}
                customStyle={{ fontSize: '12px' }}
            />
        </div>
    );

    // Render smart code block for tools with code arguments
    const renderSmartArgs = () => {
        if (!codeRenderInfo) return null;
        const { code, language, restArgs } = codeRenderInfo;
        const hasRest = Object.keys(restArgs).length > 0;

        return (
            <div className="space-y-2">
                {/* Metadata: non-code arguments shown as compact tags */}
                {hasRest && (
                    <div className="flex flex-wrap gap-1.5">
                        {Object.entries(restArgs).map(([k, v]) => (
                            <span key={k} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-xs font-mono">
                                <span className="text-gray-400">{k}:</span> {String(v)}
                            </span>
                        ))}
                    </div>
                )}
                {/* Code content with syntax highlighting */}
                <div className="bg-white rounded border border-gray-200 overflow-hidden">
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-50 border-b border-gray-200">
                        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">{language}</span>
                    </div>
                    <div className="overflow-auto max-h-[400px]">
                        <CodeHighlighter 
                            language={language}
                            code={code}
                            customStyle={{ fontSize: '12px', background: '#fff' }}
                        />
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="text-xs">
            {/* Tool call header */}
            <div 
                className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors ${
                    isResult 
                        ? 'bg-green-50 hover:bg-green-100 text-green-700' 
                        : 'bg-blue-50 hover:bg-blue-100 text-blue-700'
                }`}
                onClick={() => (hasArguments || hasResult) && setIsExpanded(!isExpanded)}
            >
                <div className={`shrink-0 ${isResult ? 'text-green-600' : 'text-blue-600'}`}>
                    {isResult ? <CheckCircle className="w-3.5 h-3.5" /> : <Wrench className="w-3.5 h-3.5" />}
                </div>
                <span className="flex-1 font-medium">
                    {isResult ? '✓ ' : '🔧 '}
                    {toolCall.name}
                    {!isResult && hasArguments && ' (...)'}
                </span>
                {(hasArguments || hasResult) && (
                    <div className="shrink-0 text-gray-400">
                        {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </div>
                )}
            </div>

            {/* Arguments/Result details */}
            {isExpanded && (
                <div className="mt-1 ml-4 pl-3 border-l-2 border-gray-200">
                    {!isResult && hasArguments && (
                        codeRenderInfo ? renderSmartArgs() : renderJsonBlock(formatJson(toolCall.arguments), "Arguments")
                    )}
                    {isResult && hasResult && renderJsonBlock(formatJson(toolCall.result), "Result")}
                </div>
            )}
        </div>
    );
};

export default ToolCallItem;
