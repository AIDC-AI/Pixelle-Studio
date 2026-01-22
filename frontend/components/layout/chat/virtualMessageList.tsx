'use client'

import { Message, OutputFile } from "@/types/message";
import { useEffect, useRef, useMemo, memo, useCallback } from "react";
import { useVirtualList, useMeasure } from "@/hooks/useVirtualList";
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

// 实质性系统操作
const SUBSTANTIAL_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'tool_call'];

// 用户交互类型的消息
const USER_INTERACTION_TYPES = ['user', 'response', 'result', 'output_files', 'error'];

interface MessageGroup {
    type: 'system_operations' | 'single';
    messages: Message[];
    isComplete?: boolean;
}

// 单个消息项组件 - 使用 memo 避免不必要的重渲染
const MessageItem = memo<{
    group: MessageGroup;
    groupIndex: number;
    isLast: boolean;
    onFilePreview?: (file: OutputFile) => void;
    onHeightChange?: (height: number) => void;
}>(({ group, groupIndex, isLast, onFilePreview, onHeightChange }) => {
    const measureRef = useMeasure(onHeightChange || (() => {}));

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
            <div ref={measureRef} className="self-start w-full max-w-[90%] mb-4">
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
            <div ref={measureRef} className={`flex flex-col mb-4 ${getMessageClass(msg)}`}>
                {renderItem(msg, isLast)}
            </div>
        );
    }
}, (prevProps, nextProps) => {
    // 自定义比较函数，只在必要时重新渲染
    return (
        prevProps.groupIndex === nextProps.groupIndex &&
        prevProps.isLast === nextProps.isLast &&
        JSON.stringify(prevProps.group) === JSON.stringify(nextProps.group)
    );
});

MessageItem.displayName = 'MessageItem';

const VirtualMessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript, onFilePreview, streamingResponse } = props;  

    const lastMessageCountRef = useRef<number>(0);
    const itemHeightsRef = useRef<Map<number, number>>(new Map());
    
    // 分组消息
    const groupedMessages = useMemo(() => {
        if (!messages || messages.length === 0) return [];
        
        const groups: MessageGroup[] = [];
        let currentSystemGroup: Message[] = [];
        
        messages.forEach((msg) => {
            const isSystemOp = SYSTEM_OPERATION_TYPES.includes(msg.type);
            const isUserInteraction = USER_INTERACTION_TYPES.includes(msg.type);
            
            if (isSystemOp) {
                currentSystemGroup.push(msg);
            } else {
                if (currentSystemGroup.length > 0) {
                    const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
                    
                    if (hasSubstantialOps) {
                        const isComplete = isUserInteraction && (msg.type === 'result' || msg.type === 'response' || msg.type === 'output_files');
                        groups.push({
                            type: 'system_operations',
                            messages: [...currentSystemGroup],
                            isComplete
                        });
                    }
                    currentSystemGroup = [];
                }
                groups.push({
                    type: 'single',
                    messages: [msg]
                });
            }
        });
        
        if (currentSystemGroup.length > 0) {
            const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
            
            if (hasSubstantialOps) {
                groups.push({
                    type: 'system_operations',
                    messages: currentSystemGroup,
                    isComplete: false
                });
            }
        }
        
        return groups;
    }, [messages]);

    // 使用虚拟列表
    const { virtualItems, totalHeight, containerRef, scrollToBottom } = useVirtualList(
        groupedMessages,
        {
            itemHeight: 150, // 预估高度
            overscan: 2,
        }
    );

    // 处理高度变化
    const handleHeightChange = useCallback((index: number, height: number) => {
        itemHeightsRef.current.set(index, height);
    }, []);

    // 自动滚动到底部
    useEffect(() => {
        if (!messages || messages.length === 0) return;
        
        const lastMessage = messages[messages.length - 1];
        const isEndMessage = lastMessage.type === 'result' || 
                            lastMessage.type === 'response' || 
                            lastMessage.type === 'error' ||
                            lastMessage.type === 'output_files';
        
        if (isEndMessage || lastMessage.type === 'user') {
            // 延迟滚动，等待渲染完成
            setTimeout(() => scrollToBottom('smooth'), 100);
        }
        
        lastMessageCountRef.current = messages.length;
    }, [messages, scrollToBottom]);

    return (
        <div 
            ref={containerRef}
            className="flex flex-1 flex-col p-4 overflow-y-auto"
            style={{ position: 'relative' }}
        >
            <div style={{ height: totalHeight, position: 'relative' }}>
                {virtualItems.map(({ index, data, offsetTop }) => (
                    <div
                        key={index}
                        style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            transform: `translateY(${offsetTop}px)`,
                        }}
                    >
                        <MessageItem
                            group={data}
                            groupIndex={index}
                            isLast={index === groupedMessages.length - 1}
                            onFilePreview={onFilePreview}
                            onHeightChange={(height) => handleHeightChange(index, height)}
                        />
                    </div>
                ))}
            </div>

            {/* 流式响应显示 */}
            {streamingResponse && (
                <div style={{ position: 'absolute', bottom: 16, left: 16, right: 16 }}>
                    {streamingResponse.includes('任务执行中') ? (
                        <div className="flex justify-center w-full py-2">
                            <div className="text-xs text-gray-400 italic">
                                {streamingResponse}
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col self-start max-w-[85%]">
                            <ResponseItem content={streamingResponse} isStreaming={true} />
                        </div>
                    )}
                </div>
            )}

            {currentScript && (
                <div className="self-start w-full max-w-[90%] mb-4">
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
        </div>
    )
}

export default VirtualMessageList;
