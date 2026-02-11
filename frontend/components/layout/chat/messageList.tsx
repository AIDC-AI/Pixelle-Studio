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

// System action type messages
const SYSTEM_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'iteration', 'log', 'evaluation', 'advice', 'system', 'thinking', 'tool_call', 'tool_result', 'response'];

// Substantial system operations (these should trigger System Process display)
const SUBSTANTIAL_OPERATION_TYPES = ['code', 'execution_result', 'skill_loaded', 'tool_call'];

// User interaction type messages (not placed in system container)
const USER_INTERACTION_TYPES = ['user', 'result', 'output_files', 'error'];

interface MessageGroup {
    type: 'system_operations' | 'single';
    messages: Message[];
    isComplete?: boolean;
}

// Optimization: wrap individual message items with memo to avoid unnecessary re-renders
const MessageItem = memo<{
    group: MessageGroup;
    groupIndex: number;
    isLast: boolean;
    onFilePreview?: (file: OutputFile) => void;
    onHeightMeasured?: (index: number, height: number) => void;
}>(({ group, groupIndex, isLast, onFilePreview, onHeightMeasured }) => {
    const itemRef = useRef<HTMLDivElement>(null);
    
    // Measure height
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
    // Optimized comparison function: fail-fast strategy
    // 1. First compare the most likely changing properties
    if (prevProps.isLast !== nextProps.isLast) return false;
    
    // 2. Compare message count
    if (prevProps.group.messages.length !== nextProps.group.messages.length) return false;
    
    // 3. Compare type and completion status
    if (prevProps.group.type !== nextProps.group.type) return false;
    if (prevProps.group.isComplete !== nextProps.group.isComplete) return false;
    
    // 4. Only compare timestamps of the first and last messages (optimize performance)
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
    // Group messages: group consecutive system operation messages together
    const groupedMessages = useMemo(() => {
        if (!messages || messages.length === 0) return [];
        
        const groups: MessageGroup[] = [];
        let currentSystemGroup: Message[] = [];
        
        messages.forEach((msg) => {
            const isSystemOp = SYSTEM_OPERATION_TYPES.includes(msg.type);
            const isUserInteraction = USER_INTERACTION_TYPES.includes(msg.type);
            
            if (isSystemOp) {
                // Add to current system operation group
                currentSystemGroup.push(msg);
            } else {
                // If there are accumulated system operations, add them first
                if (currentSystemGroup.length > 0) {
                    // Check if it contains substantial operations
                    const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
                    
                    if (hasSubstantialOps) {
                        // Only create SystemOperationGroup if it contains substantial operations
                        // Check if next message is user interaction type to determine if complete
                        const isComplete = isUserInteraction && (msg.type === 'result' || msg.type === 'response' || msg.type === 'output_files');
                        groups.push({
                            type: 'system_operations',
                            messages: [...currentSystemGroup],
                            isComplete
                        });
                    }
                    // If no substantial operations, discard these messages (do not display)
                    currentSystemGroup = [];
                }
                // Add single message
                groups.push({
                    type: 'single',
                    messages: [msg]
                });
            }
        });
        
        // Handle remaining system operations (in progress)
        if (currentSystemGroup.length > 0) {
            // Check if it contains substantial operations
            const hasSubstantialOps = currentSystemGroup.some(m => SUBSTANTIAL_OPERATION_TYPES.includes(m.type));
            
            if (hasSubstantialOps) {
                groups.push({
                    type: 'system_operations',
                    messages: currentSystemGroup,
                    isComplete: false
                });
            }
            // If no substantial operations, discard these messages
        }
        
        return groups;
    }, [messages]);
    
    // Track if user has manually scrolled
    const userScrolledRef = useRef(false);
    const scrollTimeoutRef = useRef<NodeJS.Timeout>(null);
    
    // Listen for user scroll
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        
        const handleScroll = () => {
            // Clear previous timer
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
            
            // Check if at bottom
            const threshold = 50;
            const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            const isAtBottom = scrollBottom < threshold;
            
            // If user scrolls to bottom, reset flag
            if (isAtBottom) {
                userScrolledRef.current = false;
            } else {
                // User scrolled up, set flag
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
    
    // Optimize scrolling: use requestAnimationFrame
    const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
        requestAnimationFrame(() => {
            chatEndRef.current?.scrollIntoView({ behavior });
            userScrolledRef.current = false; // Reset scroll flag
        });
    }, []);
    
    // Smart scrolling: only auto-scroll if user is already at the bottom
    useEffect(() => {
        if (!messages || messages.length === 0) return;
        
        // Check if session has switched
        const sessionChanged = activeSessionId !== lastSessionIdRef.current;
        if (sessionChanged) {
            lastSessionIdRef.current = activeSessionId;
            userScrolledRef.current = false; // Reset scroll flag
            // When session switches, delay scroll to bottom to ensure content is rendered
            setTimeout(() => scrollToBottom('auto'), 100);
            return;
        }
        
        // If user has not manually scrolled up, auto-scroll to bottom
        if (!userScrolledRef.current) {
            const lastMessage = messages[messages.length - 1];
            const isEndMessage = lastMessage.type === 'result' || 
                                lastMessage.type === 'response' || 
                                lastMessage.type === 'error' ||
                                lastMessage.type === 'output_files';
            
            // Use smooth scroll for final messages or user messages
            if (isEndMessage || lastMessage.type === 'user') {
                scrollToBottom('smooth');
            } else {
                // Use instant scroll for other messages
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
                    // Use more stable key, based on message content instead of index
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
                {/* Streaming response display */}
                {streamingResponse && (
                    streamingResponse.includes('Task in progress') ? (
                        // Loading state: small font, no logo, displayed at the top
                        <div className="flex justify-center w-full py-2">
                            <div className="text-xs text-gray-400 italic">
                                {streamingResponse}
                            </div>
                        </div>
                    ) : (
                        // Normal response: display bot logo and content
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
