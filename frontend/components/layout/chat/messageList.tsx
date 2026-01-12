'use client'

import { Message } from "@/types/message";
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
import ToolCallItem from "./items/toolCallItem";
import ToolResultItem from "./items/toolResultItem";
import SystemOperationGroup from "./items/systemOperationGroup";

interface IProps {
    messages?: Message[] | null
    currentScript?: string | null
    shouldScrollToBottom?: boolean
}

// 系统操作类型的消息
const SYSTEM_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'iteration', 'log', 'evaluation', 'advice', 'system', 'tool_call', 'tool_result'];

// 用户交互类型的消息（不放在系统容器里）
const USER_INTERACTION_TYPES = ['user', 'response', 'result', 'output_files', 'error'];

interface MessageGroup {
    type: 'system_operations' | 'single';
    messages: Message[];
    isComplete?: boolean;
    id: string; // 添加唯一 ID
}

// 优化：将单个消息项组件化并使用 memo
const MessageItem = memo(({ msg, isLast }: { 
    msg: Message; 
    isLast: boolean;
}) => {
    const renderContent = () => {
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
                return <OutputFilesItem files={msg.outputFiles || []} />
            case 'tool_call':
                return msg.toolCall ? <ToolCallItem toolCall={msg.toolCall} /> : null
            case 'tool_result':
                return msg.toolResult ? <ToolResultItem toolResult={msg.toolResult} /> : null
        }
        return null;
    };

    return <div>{renderContent()}</div>;
}, (prevProps, nextProps) => {
    // 自定义比较函数：只有当消息内容真正改变时才重新渲染
    return (
        prevProps.msg.type === nextProps.msg.type &&
        prevProps.msg.content === nextProps.msg.content &&
        prevProps.msg.timestamp === nextProps.msg.timestamp &&
        prevProps.isLast === nextProps.isLast
    );
});

MessageItem.displayName = 'MessageItem';

// 虚拟化的消息组渲染器
const VirtualMessageGroup = memo(({ group, isLast }: { group: MessageGroup; isLast: boolean }) => {
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
    };

    if (group.type === 'system_operations') {
        return (
            <div className="self-start w-full max-w-[90%] mb-4">
                <SystemOperationGroup isComplete={group.isComplete}>
                    {group.messages.map((msg, msgIndex) => (
                        <MessageItem
                            key={`${msg.timestamp}-${msgIndex}`}
                            msg={msg}
                            isLast={isLast && msgIndex === group.messages.length - 1}
                        />
                    ))}
                </SystemOperationGroup>
            </div>
        );
    } else {
        const msg = group.messages[0];
        return (
            <div className={`flex flex-col mb-4 ${getMessageClass(msg)}`}>
                <MessageItem
                    msg={msg}
                    isLast={isLast}
                />
            </div>
        );
    }
}, (prevProps, nextProps) => {
    return (
        prevProps.group.id === nextProps.group.id &&
        prevProps.group.messages.length ===  nextProps.group.messages.length && 
        prevProps.group.isComplete === nextProps.group.isComplete &&
        prevProps.isLast === nextProps.isLast
    );
});

VirtualMessageGroup.displayName = 'VirtualMessageGroup';

const MessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript } = props;  

    const containerRef = useRef<HTMLDivElement>(null);
    const shouldAutoScrollRef = useRef(true);
    const lastMessageCountRef = useRef(0);
    
    // 分组消息：将连续的系统操作消息放在一起
    const groupedMessages = useMemo(() => {
        if (!messages || messages.length === 0) return [];
        
        const groups: MessageGroup[] = [];
        let currentSystemGroup: Message[] = [];
        let groupIdCounter = 0;
        
        messages.forEach((msg, index) => {
            const isSystemOp = SYSTEM_OPERATION_TYPES.includes(msg.type);
            const isUserInteraction = USER_INTERACTION_TYPES.includes(msg.type);
            
            if (isSystemOp) {
                currentSystemGroup.push(msg);
            } else {
                if (currentSystemGroup.length > 0) {
                    const isComplete = isUserInteraction && (msg.type === 'result' || msg.type === 'response' || msg.type === 'output_files');
                    groups.push({
                        type: 'system_operations',
                        messages: [...currentSystemGroup],
                        isComplete,
                        id: `group-${groupIdCounter++}`
                    });
                    currentSystemGroup = [];
                }
                groups.push({
                    type: 'single',
                    messages: [msg],
                    id: `single-${msg.timestamp}-${index}`
                });
            }
        });
        
        if (currentSystemGroup.length > 0) {
            groups.push({
                type: 'system_operations',
                messages: currentSystemGroup,
                isComplete: false,
                id: `group-${groupIdCounter++}`
            });
        }
        
        return groups;
    }, [messages]);
    
    // 自动滚动到底部
    const scrollToBottom = useCallback(() => {
        if (containerRef.current && shouldAutoScrollRef.current) {
            requestAnimationFrame(() => {
                if (containerRef.current) {
                    containerRef.current.scrollTop = containerRef.current.scrollHeight;
                }
            });
        }
    }, []);

    // 检测用户是否手动滚动
    const handleScroll = useCallback(() => {
        if (!containerRef.current) return;
        
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
        
        shouldAutoScrollRef.current = isNearBottom;
    }, []);

    // 当消息更新时滚动
    useEffect(() => {
        if (!messages || messages.length === 0) return;
        
        const lastMessage = messages[messages.length - 1];
        const isEndMessage = lastMessage.type === 'result' || 
                            lastMessage.type === 'response' || 
                            lastMessage.type === 'error' ||
                            lastMessage.type === 'output_files';
        
        // 新消息到来时，如果是用户消息或结束消息，强制滚动到底部
        if (lastMessage.type === 'user' || isEndMessage) {
            shouldAutoScrollRef.current = true;
            scrollToBottom();
        } 
        // 其他新消息时，只有在自动滚动模式下才滚动
        else if (messages.length > lastMessageCountRef.current) {
            scrollToBottom();
        }
        
        lastMessageCountRef.current = messages.length;
    }, [messages, scrollToBottom]);

    // 使用 IntersectionObserver 优化渲染（可选）
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        container.addEventListener('scroll', handleScroll, { passive: true });
        
        return () => {
            container.removeEventListener('scroll', handleScroll);
        };
    }, [handleScroll]);

    return (
        <div 
            ref={containerRef}
            className="flex flex-1 flex-col p-4 overflow-y-auto"
            style={{ 
                overscrollBehavior: 'contain',
                WebkitOverflowScrolling: 'touch'
            }}
        >
            <div className="flex flex-col gap-0">
                {groupedMessages.map((group, index) => (
                    <VirtualMessageGroup
                        key={group.id}
                        group={group}
                        isLast={index === groupedMessages.length - 1}
                    />
                ))}
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
        </div>
    )
}

export default memo(MessageList);
