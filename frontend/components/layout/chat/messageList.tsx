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

'use client'

import { Message, OutputFile } from "@/types/message";
import { useEffect, useRef, useMemo, memo, useCallback } from "react";
import UserItem from "./items/userItem";
import SystemItem from "./items/systemItem";
import IterationItem from "./items/iterationItem";
import LogItem from "./items/logItem";
import EvalutaionItem from "./items/evaluationItem";
import AdviceItem from "./items/adviceItem";
import ResultItem from "./items/resultItem";
import ErrorItem from "./items/errorItem";
import CodeItem from "./items/codeItem";
import ExecutionResultItem from "./items/executionResultItem";
import ResponseItem from "./items/responseItem";
import SkillLoadedItem from "./items/skillLoadedItem";
import OutputFilesItem from "./items/outputFilesItem";
import SystemOperationGroup from "./items/systemOperationGroup";
import ThinkingItem from "./items/thinkingItem";
import ToolCallItem from "./items/toolCallItem";
import { useApp } from "@/context";
import LoadingSpinner from "@/components/ui/loadingSpinner";

interface IProps {
    messages?: Message[] | null
    currentScript?: string | null
    shouldScrollToBottom?: boolean
    onFilePreview?: (file: OutputFile) => void
    streamingResponse?: string
    isLoading?: boolean
    isCodeBlock?: boolean
}

// 系统操作类型的消息
const SYSTEM_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'iteration', 'log', 'evaluation', 'advice', 'system', 'thinking', 'tool_call', 'tool_result'];

// 实质性系统操作（这些才应该触发System Process的显示）
const SUBSTANTIAL_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'tool_call'];

// 用户交互类型的消息（不放在系统容器里）
const USER_INTERACTION_TYPES = ['user', 'response', 'result', 'output_files', 'error'];

interface MessageGroup {
    type: 'system_operations' | 'single';
    messages: Message[];
    isComplete?: boolean;
}

// 优化：使用 memo 包装单个消息项，避免不必要的重渲染
const MessageItem = memo<{
    group: MessageGroup;
    groupIndex: number;
    isLast: boolean;
    onFilePreview?: (file: OutputFile) => void;
    onHeightMeasured?: (index: number, height: number) => void;
}>(({ group, groupIndex, isLast, onFilePreview, onHeightMeasured }) => {
    const itemRef = useRef<HTMLDivElement>(null);
    
    // 测量高度
    useEffect(() => {
        if (itemRef.current && onHeightMeasured) {
            const height = itemRef.current.getBoundingClientRect().height;
            onHeightMeasured(groupIndex, height);
        }
    }, [groupIndex, onHeightMeasured, group]);
    
    const renderItem = useCallback((msg: Message, isLastInGroup: boolean) => {
        switch (msg.type) {
            case 'user':
                return <UserItem content={msg.content} files={msg.outputFiles} />
            case 'system':
                return <SystemItem content={msg.content} isLast={isLastInGroup} />
            case 'iteration':
                return <IterationItem content={msg.content} />
            case 'log':
                return <LogItem content={msg.content} />
            case 'evaluation':
                return <EvalutaionItem content={msg.content} />
            case 'advice':
                return <AdviceItem content={msg.content} />
            case 'result':
                return <ResultItem content={msg.content} />
            case 'error':
                return <ErrorItem content={msg.content} />
            case 'code':
                return (
                    <CodeItem 
                        code={msg.codeData?.code || msg.content} 
                        executionCount={msg.codeData?.executionCount}
                        reasoning={msg.codeData?.reasoning}
                    />
                )
            case 'execution_result':
                return (
                    <ExecutionResultItem 
                        result={msg.executionResult || msg.content}
                        executionCount={msg.codeData?.executionCount}
                    />
                )
            case 'response':
                return <ResponseItem content={msg.content} />
            case 'skill_loaded':
                return <SkillLoadedItem skillName={msg.skillName || msg.content} />
            case 'output_files':
                return <OutputFilesItem files={msg.outputFiles || []} onFilePreview={onFilePreview} />
            case 'thinking':
                return <ThinkingItem content={msg.content} />
            case 'tool_call':
                return <ToolCallItem toolCall={msg.toolCall} /> 
            case 'tool_result':
                return <ToolCallItem toolCall={msg.toolResult} isResult={true} />
        }
        return null;
    }, [onFilePreview]);

    const getMessageClass = useCallback((msg: Message) => {
        if (msg.type === 'user') {
            return 'self-end max-w-[85%]';
        }
        if (msg.type === 'result' || msg.type === 'output_files') {
            return 'self-start w-full max-w-[90%]';
        }
        if (msg.type === 'response') {
            return 'self-start max-w-[85%]';
        }
        if (msg.type === 'error') {
            return 'self-start max-w-[80%]';
        }
        return 'self-start max-w-[80%]';
    }, []);

    if (group.type === 'system_operations') {
        return (
            <div key={`group-${groupIndex}`} className="self-start w-full max-w-[90%]">
                <SystemOperationGroup isComplete={group.isComplete}>
                    {group.messages.map((msg, msgIndex) => (
                        <div key={`${groupIndex}-${msgIndex}`}>
                            {renderItem(msg, isLast && msgIndex === group.messages.length - 1)}
                        </div>
                    ))}
                </SystemOperationGroup>
            </div>
        );
    } else {
        const msg = group.messages[0];
        return (
            <div key={`single-${groupIndex}`} className={`flex flex-col ${getMessageClass(msg)}`}>
                {renderItem(msg, isLast)}
            </div>
        );
    }
}, (prevProps, nextProps) => {
    // 优化的比较函数：快速失败策略
    // 1. 先比较最可能变化的属性
    if (prevProps.isLast !== nextProps.isLast) return false;
    
    // 2. 比较消息数量
    if (prevProps.group.messages.length !== nextProps.group.messages.length) return false;
    
    // 3. 比较类型和完成状态
    if (prevProps.group.type !== nextProps.group.type) return false;
    if (prevProps.group.isComplete !== nextProps.group.isComplete) return false;
    
    // 4. 只比较第一个和最后一个消息的时间戳（优化性能）
    const prevMsgs = prevProps.group.messages;
    const nextMsgs = nextProps.group.messages;
    
    if (prevMsgs.length > 0) {
        if (prevMsgs[0].timestamp !== nextMsgs[0].timestamp) return false;
        if (prevMsgs.length > 1 && 
            prevMsgs[prevMsgs.length - 1].timestamp !== nextMsgs[nextMsgs.length - 1].timestamp) {
            return false;
        }
    }
    
    return true;
});

MessageItem.displayName = 'MessageItem';

const MessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript, onFilePreview, streamingResponse, isLoading, isCodeBlock } = props;  
    
    const { activeSessionId } = useApp()
    
    const chatEndRef = useRef<HTMLDivElement>(null);
    const lastMessageCountRef = useRef<number>(0);
    const containerRef = useRef<HTMLDivElement>(null);
    const lastSessionIdRef = useRef<string | undefined>(activeSessionId);
    // console.log('messages--->', messages)
    // 分组消息：将连续的系统操作消息放在一起
    const groupedMessages = useMemo(() => {
        if (!messages || messages.length === 0) return [];
        
        const groups: MessageGroup[] = [];
        let currentSystemGroup: Message[] = [];
        
        messages.forEach((msg) => {
            const isSystemOp = SYSTEM_OPERATION_TYPES.includes(msg.type);
            const isUserInteraction = USER_INTERACTION_TYPES.includes(msg.type);
            
            if (isSystemOp) {
                // 添加到当前系统操作组
                currentSystemGroup.push(msg);
            } else {
                // 如果有累积的系统操作，先添加它们
                if (currentSystemGroup.length > 0) {
                    // 检查是否包含实质性操作
                    const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
                    
                    if (hasSubstantialOps) {
                        // 只有包含实质性操作才创建SystemOperationGroup
                        // 检查下一个消息是否是用户交互类型来判断是否完成
                        const isComplete = isUserInteraction && (msg.type === 'result' || msg.type === 'response' || msg.type === 'output_files');
                        groups.push({
                            type: 'system_operations',
                            messages: [...currentSystemGroup],
                            isComplete
                        });
                    }
                    // 如果没有实质性操作，则丢弃这些消息（不显示）
                    currentSystemGroup = [];
                }
                // 添加单独的消息
                groups.push({
                    type: 'single',
                    messages: [msg]
                });
            }
        });
        
        // 处理剩余的系统操作（正在进行中）
        if (currentSystemGroup.length > 0) {
            // 检查是否包含实质性操作
            const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
            
            if (hasSubstantialOps) {
                groups.push({
                    type: 'system_operations',
                    messages: currentSystemGroup,
                    isComplete: false
                });
            }
            // 如果没有实质性操作，则丢弃这些消息
        }
        
        return groups;
    }, [messages]);
    
    // 跟踪用户是否手动滚动过
    const userScrolledRef = useRef(false);
    const scrollTimeoutRef = useRef<NodeJS.Timeout>(null);
    
    // 监听用户滚动
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        
        const handleScroll = () => {
            // 清除之前的定时器
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
            
            // 检查是否在底部
            const threshold = 50;
            const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            const isAtBottom = scrollBottom < threshold;
            
            // 如果用户滚动到底部，重置标记
            if (isAtBottom) {
                userScrolledRef.current = false;
            } else {
                // 用户向上滚动，设置标记
                userScrolledRef.current = true;
            }
        };
        
        container.addEventListener('scroll', handleScroll, { passive: true });
        return () => {
            container.removeEventListener('scroll', handleScroll);
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
        };
    }, []);
    
    // 优化滚动：使用 requestAnimationFrame
    const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
        requestAnimationFrame(() => {
            chatEndRef.current?.scrollIntoView({ behavior });
            userScrolledRef.current = false; // 重置滚动标记
        });
    }, []);
    
    // 智能滚动：只在用户已经在底部时才自动滚动
    useEffect(() => {
        if (!messages || messages.length === 0) return;
        
        // 检查是否切换了会话
        // 检查是否切换了会话
        const sessionChanged = activeSessionId !== lastSessionIdRef.current;
        if (sessionChanged) {
            lastSessionIdRef.current = activeSessionId;
            userScrolledRef.current = false; // 重置滚动标记
            // 会话切换时，延迟滚动到底部以确保内容已渲染
            setTimeout(() => scrollToBottom('auto'), 100);
            return;
        }
        
        // 如果用户没有手动向上滚动，就自动滚动到底部
        if (!userScrolledRef.current) {
            const lastMessage = messages[messages.length - 1];
            const isEndMessage = lastMessage.type === 'result' || 
                                lastMessage.type === 'response' || 
                                lastMessage.type === 'error' ||
                                lastMessage.type === 'output_files';
            
            // 最终消息或用户消息时使用平滑滚动
            if (isEndMessage || lastMessage.type === 'user') {
                scrollToBottom('smooth');
            } else {
                // 其他消息使用即时滚动
                scrollToBottom('auto');
            }
        }
        
        lastMessageCountRef.current = messages.length;
    }, [messages, scrollToBottom, activeSessionId]);
    
    return (
        <div className="relative flex flex-1 min-h-0">
            {/* Loading overlay when switching sessions */}
            {isLoading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-50/70 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-3">
                        <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-orange-500"></div>
                        <div className="text-xs text-gray-500">Loading messages…</div>
                    </div>
                </div>
            )}

            <div 
                ref={containerRef} 
                className={[
                    "flex flex-1 flex-col p-4 overflow-y-auto gap-4 overscroll-none transition-opacity duration-200",
                    isLoading ? "opacity-0 pointer-events-none" : "opacity-100 animate-fade-in"
                ].join(" ")}
                style={{ 
                    willChange: 'scroll-position',
                    contain: 'layout style paint'
                }}
            >
                {groupedMessages.map((group, groupIndex) => {
                    // 使用更稳定的 key，基于消息内容而不是索引
                    const key = group.type === 'system_operations' 
                        ? `sys-${group.messages[0]?.timestamp || groupIndex}`
                        : `msg-${group.messages[0]?.timestamp || groupIndex}`;
                    
                    return (
                        <MessageItem
                            key={key}
                            group={group}
                            groupIndex={groupIndex}
                            isLast={groupIndex === groupedMessages.length - 1}
                            onFilePreview={onFilePreview}
                        />
                    );
                })}
                {/* 流式响应显示 */}
                {streamingResponse && (
                    streamingResponse.includes('任务执行中') ? (
                        // 加载状态：小字体，无logo，显示在上方
                        <div className="flex justify-center w-full py-2">
                            <div className="text-xs text-gray-400 italic">
                                {streamingResponse}
                            </div>
                        </div>
                    ) : (
                        // 正常响应：显示机器人logo和内容
                        <div className="flex flex-col self-start max-w-[85%]">
                            <ResponseItem content={streamingResponse} isStreaming={true} />
                        </div>
                    )
                )}
                {isCodeBlock && <div className="w-full flex justify-center items-center">
                    <LoadingSpinner type="dots" />
                </div>}
                {currentScript && (
                    <div className="self-start w-full max-w-[90%]">
                        <div className="bg-slate-800 rounded-xl p-4">
                            <div className="flex items-center gap-2 mb-3">
                                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                <span className="ml-2 text-slate-400 text-sm">Current Workflow Script</span>
                            </div>
                            <pre className="text-slate-200 text-sm font-mono overflow-x-auto whitespace-pre-wrap">{currentScript}</pre>
                        </div>
                    </div>
                )}
                <div ref={chatEndRef} />
            </div>
        </div>
    )
}

export default MessageList;
