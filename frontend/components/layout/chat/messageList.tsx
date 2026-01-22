'use client'

import { Message, OutputFile } from "@/types/message";
import { useEffect, useRef, useMemo } from "react";
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

interface IProps {
    messages?: Message[] | null
    currentScript?: string | null
    shouldScrollToBottom?: boolean
    onFilePreview?: (file: OutputFile) => void
    streamingResponse?: string
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

const MessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript, shouldScrollToBottom = true, onFilePreview, streamingResponse } = props;  

    const chatEndRef = useRef<HTMLDivElement>(null);
    const lastMessageCountRef = useRef<number>(0);
    
    // 分组消息：将连续的系统操作消息放在一起
    const groupedMessages = useMemo(() => {
        if (!messages || messages.length === 0) return [];
        
        const groups: MessageGroup[] = [];
        let currentSystemGroup: Message[] = [];
        
        messages.forEach((msg, index) => {
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
    
    // 只在收到最终结果时滚动到底部
    useEffect(() => {
        if (!messages || messages.length === 0) return;
        
        const lastMessage = messages[messages.length - 1];
        const isEndMessage = lastMessage.type === 'result' || 
                            lastMessage.type === 'response' || 
                            lastMessage.type === 'error' ||
                            lastMessage.type === 'output_files';
        
        // 只有在是最终消息或者是用户消息时才滚动
        if (isEndMessage || lastMessage.type === 'user') {
            chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
        
        lastMessageCountRef.current = messages.length;
    }, [messages]);
    
    const renderItem = (msg: Message, isLast: boolean) => {
        switch (msg.type) {
            case 'user':
                return <UserItem content={msg.content} files={msg.outputFiles} />
            case 'system':
                return <SystemItem content={msg.content} isLast={isLast} />
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
    }

    // 获取单独消息的样式类
    const getMessageClass = (msg: Message) => {
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
    }

    return (
        <div className="flex flex-1 flex-col p-4 overflow-y-auto gap-4">
            {groupedMessages.map((group, groupIndex) => {
                if (group.type === 'system_operations') {
                    // 渲染系统操作组
                    return (
                        <div key={`group-${groupIndex}`} className="self-start w-full max-w-[90%]">
                            <SystemOperationGroup isComplete={group.isComplete}>
                                {group.messages.map((msg, msgIndex) => (
                                    <div key={`${groupIndex}-${msgIndex}`}>
                                        {renderItem(msg, groupIndex === groupedMessages.length - 1 && msgIndex === group.messages.length - 1)}
                                    </div>
                                ))}
                            </SystemOperationGroup>
                        </div>
                    );
                } else {
                    // 渲染单独消息
                    const msg = group.messages[0];
                    return (
                        <div key={`single-${groupIndex}`} className={`flex flex-col ${getMessageClass(msg)}`}>
                            {renderItem(msg, groupIndex === groupedMessages.length - 1)}
                        </div>
                    );
                }
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
    )
}

export default MessageList;
