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
    
    const renderItem = (msg: Message) => {
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
        }
        return null;
    }

    return (
        <div className="flex flex-1 flex-col p-4 overflow-y-auto gap-3">
            {messages?.map((msg, idx) => (
                <div key={idx} className={`message ${msg.type}`}>
                    {
                        renderItem(msg)
                    }
                </div>
            ))}
            {currentScript && (
                <div className="message system">
                    <strong>Current Workflow Script:</strong>
                    <div className="mt-2.5 p-2.5 bg-gray-800 text-gray-100 rounded overflow-x-auto whitespace-pre-wrap font-mono">{currentScript}</div>
                </div>
            )}
            <div ref={chatEndRef} />
        </div>
    )
}

export default MessageList;