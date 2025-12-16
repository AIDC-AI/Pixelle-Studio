'use client'

import { Message } from "@/types/message";
import { useEffect, useRef } from "react";

interface IProps {
    messages: Message[]
    currentScript?: string | null
}

const MessageList: React.FC<IProps> = (props) => {
    const { messages, currentScript } = props;  

    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);
    
    return (
        <div className="flex flex-1 flex-col border-1 border-gray-200 rounded-lg p-5 overflow-y-auto mb-5 bg-[#f9f9f9] gap-3">
            {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.type}`}>
                    {msg.type === 'user' && <div>{msg.content}</div>}
                    {msg.type === 'system' && <div><em>{msg.content}</em></div>}
                    {msg.type === 'iteration' && <div><strong>{msg.content}</strong></div>}
                    {msg.type === 'log' && <div className="log-entry">{msg.content}</div>}
                    {msg.type === 'evaluation' && <div style={{ background: '#f0f8ff', padding: '8px', borderRadius: '4px' }}><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</pre></div>}
                    {msg.type === 'advice' && <div style={{ background: '#fffacd', padding: '8px', borderRadius: '4px' }}><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</pre></div>}
                    {msg.type === 'result' && (
                    <div>
                        <strong>Result:</strong>
                        <pre>{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}</pre>
                    </div>
                    )}
                    {msg.type === 'error' && <div style={{ color: 'red' }}>Error: {msg.content}</div>}
                </div>
            ))}
            {currentScript && (
                <div className="message system">
                    <strong>Current Workflow Script:</strong>
                    <div className="script-preview">{currentScript}</div>
                </div>
            )}
            <div ref={chatEndRef} />
        </div>
    )
}

export default MessageList;