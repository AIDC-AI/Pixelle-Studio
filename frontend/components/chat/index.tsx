'use client'

import { Message } from "@/types/message";
import { useState } from "react";
import MessageList from "./messageList";
import { Button, Input, Upload, UploadFile, UploadProps } from "antd";
import { FileOutlined } from '@ant-design/icons';
import { api } from "@/lib/api";
import { useApp } from "@/context";

const Chat = () => {
    const { config } = useApp();
    
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [fileUrls, setFileUrls] = useState<string[]>([]);
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const [input, setInput] = useState<string>('');
    
    const handleChange: UploadProps['onChange'] = (info) => {
        let newFileList = [...info.fileList];

        // 1. Limit the number of uploaded files
        // Only to show two recent uploaded files, and old ones will be replaced by the new
        // newFileList = newFileList.slice(-2);

        // 2. Read from response and show file link
        newFileList = newFileList.map((file) => {
        if (file.response) {
            // Component will show file.url as link
            file.url = file.response.url;
        }
            return file;
        });

        setFileList(newFileList);
    };
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!input.trim() || isProcessing) return;
    
        const userMsg = input;
        const currentFileUrls = fileList?.filter((file) => !!file?.url && file?.url !== '').map((file) => file.url!)
        setInput('');
        setFileList([]);
        setIsProcessing(true);
        setCurrentScript(null);
    
        // Add user message
        setMessages(prev => [...prev, { type: 'user', content: userMsg, timestamp: Date.now() }]);
    
        try {
          // 1. Create Chat (backend will auto-select tools)
          const { chat_id } = await api.createChat(userMsg, config, currentFileUrls);
    
          // 2. Connect WebSocket
          const ws = new WebSocket(api.getWebSocketUrl(chat_id));
    
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
    
            if (data.type === 'iteration_start') {
              setMessages(prev => [...prev, { 
                type: 'iteration', 
                content: `🔄 Starting iteration ${data.iteration}/${data.max_iterations}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              }]);
            } else if (data.type === 'iteration_end') {
              const statusEmoji = data.status === 'success' ? '✅' : data.status === 'failed' ? '❌' : '🔁';
              setMessages(prev => [...prev, { 
                type: 'iteration', 
                content: `${statusEmoji} Iteration ${data.iteration} ${data.status}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              }]);
            } else if (data.type === 'script') {
              setCurrentScript(data.content);
              setMessages(prev => [...prev, { 
                type: 'system', 
                content: `📝 Generated script (iteration ${data.iteration})`, 
                timestamp: Date.now(),
                iteration: data.iteration
              }]);
            } else if (data.type === 'log') {
              setMessages(prev => [...prev, { 
                type: 'log', 
                content: `[${data.stream || 'LOG'}] ${data.content}`, 
                timestamp: Date.now() 
              }]);
            } else if (data.type === 'evaluation_result') {
              const emoji = data.meets_requirement ? '✅' : '⚠️';
              setMessages(prev => [...prev, { 
                type: 'evaluation', 
                content: `${emoji} Evaluation (iteration ${data.iteration}): ${data.meets_requirement ? 'PASS' : 'FAIL'} (confidence: ${(data.confidence_score * 100).toFixed(0)}%)\nReason: ${data.reason}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              }]);
            } else if (data.type === 'revision_advice') {
              setMessages(prev => [...prev, { 
                type: 'advice', 
                content: `💡 Revision advice (iteration ${data.iteration}):\n${data.advice.advice || JSON.stringify(data.advice, null, 2)}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              }]);
            } else if (data.type === 'final_result') {
              // 最终结果 - 现在才关闭连接
              const emoji = data.status === 'success' ? '🎉' : '❌';
              setMessages(prev => [...prev, { 
                type: 'result', 
                content: `${emoji} Final result (${data.total_iterations} iterations): ${data.status}\n${data.result ? JSON.stringify(data.result, null, 2) : data.error || ''}`, 
                timestamp: Date.now() 
              }]);
              setIsProcessing(false);
              ws.close();
            } else if (data.type === 'result') {
              // 兼容旧的 result 消息（如果有的话）
              setMessages(prev => [...prev, { type: 'result', content: data.content, timestamp: Date.now() }]);
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
        <div className="flex flex-col w-full h-full p-8">
            <MessageList 
                messages={messages} 
                currentScript={currentScript} 
            />
            <div className='flex flex-row gap-2 p-2'>
                <Upload
                    fileList={fileList}
                    action={'http://localhost:8001/api/upload'}
                    onChange={handleChange}
                    multiple
                    disabled={isProcessing}
                    showUploadList={{
                        extra: ({ size = 0 }) => (
                            <span style={{ color: '#cccccc' }}>({(size / 1024 / 1024).toFixed(2)}MB)</span>
                        )
                    }}
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
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey && !isProcessing) {
                            e.preventDefault();
                            handleSubmit(e);
                        }
                    }}
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
    );
};

export default Chat;