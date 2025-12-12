'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';
import LeftPanel from '@/components/leftPanel';
import { useApp } from '@/context';
import { Button, Input, Upload } from 'antd';
import { FileOutlined } from '@ant-design/icons';

import type { UploadFile } from 'antd';

interface Message {
    type: 'user' | 'system' | 'log' | 'script' | 'result' | 'error';
    content: any;
    timestamp: number;
}

export default function Home() {
    const { config, setConfig } = useApp();

    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isProcessing) return;

        const userMsg = input;
        setInput('');
        setIsProcessing(true);
        setCurrentScript(null);

        // Add user message
        setMessages(prev => [...prev, { type: 'user', content: userMsg, timestamp: Date.now() }]);

        try {
            // 1. Create Chat (backend will auto-select tools)
            const { chat_id } = await api.createChat(userMsg, config);

            // 2. Connect WebSocket
            const ws = new WebSocket(api.getWebSocketUrl(chat_id));

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'script') {
                    setCurrentScript(data.content);
                    setMessages(prev => [...prev, { type: 'system', content: 'Generated Workflow Script', timestamp: Date.now() }]);
                } else if (data.type === 'log') {
                    // Append log to the last message if it's a log container, or create new
                    // For simplicity, just add as message
                    setMessages(prev => [...prev, { type: 'log', content: `[${data.stream || 'LOG'}] ${data.content}`, timestamp: Date.now() }]);
                } else if (data.type === 'result') {
                    setMessages(prev => [...prev, { type: 'result', content: data.content, timestamp: Date.now() }]);
                    setIsProcessing(false);
                    ws.close();
                } else if (data.type === 'error') {
                    setMessages(prev => [...prev, { type: 'error', content: data.content, timestamp: Date.now() }]);
                    setIsProcessing(false);
                    ws.close();
                } else if (data.type === 'status') {
                    setMessages(prev => [...prev, { type: 'system', content: data.content, timestamp: Date.now() }]);
                }
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                setMessages(prev => [...prev, { type: 'error', content: 'Connection error', timestamp: Date.now() }]);
                setIsProcessing(false);
            };

        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { type: 'error', content: 'Failed to start chat', timestamp: Date.now() }]);
            setIsProcessing(false);
        }
    };

    return (
        <div className="w-screen h-screen flex">
            <LeftPanel />

            <div className="flex flex-col w-full h-full p-8">
                <div className="chat-window">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`message ${msg.type}`}>
                            {msg.type === 'user' && <div>{msg.content}</div>}
                            {msg.type === 'system' && <div><em>{msg.content}</em></div>}
                            {msg.type === 'log' && <div className="log-entry">{msg.content}</div>}
                            {msg.type === 'result' && (
                                <div>
                                    <strong>Result:</strong>
                                    <pre>{JSON.stringify(msg.content, null, 2)}</pre>
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

                <div className='flex flex-row gap-2 p-2'>
                    <Upload
                        fileList={fileList}
                        onChange={({ fileList: newFileList }) => setFileList(newFileList)}
                        beforeUpload={() => false} // 阻止自动上传
                        multiple
                        disabled={isProcessing}
                    >
                        <Button icon={<FileOutlined />} disabled={isProcessing}>
                            {fileList.length > 0 && `(${fileList.length})`}
                        </Button>
                    </Upload>
                </div>
                <div className="border border-gray-200 rounded-lg py-2 flex flex-col gap-2">
                    <Input.TextArea
                        style={{ resize: 'none' }}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Describe your task..."
                        disabled={isProcessing}
                        variant="borderless"
                    />
                    <div className='flex justify-end px-2'>
                        <Button
                            type="primary"
                            disabled={isProcessing}
                            onClick={handleSubmit}
                        >
                            {isProcessing ? 'Processing...' : 'Send'}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
