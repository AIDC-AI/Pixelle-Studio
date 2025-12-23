'use client'

import { Message } from "@/types/message";
import { useEffect, useRef } from "react";
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

interface IProps {
    messages?: Message[] | null
    currentScript?: string | null
}

const MessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript } = props;  

    const chatEndRef = useRef<HTMLDivElement>(null);
    
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);
    
    const renderItem = (msg: Message, index: number) => {
        switch (msg.type) {
            case 'user':
                return <UserItem content={msg.content} />
            case 'system':
                return <SystemItem content={msg.content} />
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
        }
        return null;
    }

    // Calculate appropriate wrapper class based on message type
    const getMessageClass = (msg: Message) => {
        if (msg.type === 'user') {
            return 'self-end max-w-[85%]';
        }
        if (msg.type === 'code' || msg.type === 'execution_result' || msg.type === 'result' || msg.type === 'output_files') {
            return 'self-start w-full max-w-[90%]';
        }
        if (msg.type === 'response') {
            return 'self-start max-w-[85%]';
        }
        if (msg.type === 'system' || msg.type === 'skill_loaded') {
            return 'self-center';
        }
        return 'self-start max-w-[80%]';
    }

    return (
        <div className="flex flex-1 flex-col p-4 overflow-y-auto gap-4">
            {messages?.map((msg, idx) => (
                <div key={idx} className={`flex flex-col ${getMessageClass(msg)}`}>
                    {renderItem(msg, idx)}
                </div>
            ))}
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
