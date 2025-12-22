'use client'

import { Message } from "@/types/message";
import { useState } from "react";
import MessageList from "./messageList";
import { Upload, UploadFile, UploadProps } from "antd";
import { api } from "@/lib/api";
import { useApp } from "@/context";
import { MAX_SESSION_COUNT, sessionAPI } from "@/lib/session";
import { Loader2, Plus, Send, Trash2 } from "lucide-react";

const Chat = () => {
    const { 
      config, 
      activeSessionId, 
      setActiveSessionId,
      setSessions,
      sessionMessages,
      setSessionMessages
    } = useApp();
    
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const [input, setInput] = useState<string>('');
    
    const addNewSession = (title: string) => {
        const timestamp = Date.now()
        const id = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        const session = {
            id,
            timestamp,
            title
        }
        setActiveSessionId(id)
        // 超出上限，去掉最后一个的元素
        setSessions(prev => {
            const arr = [session, ...prev]
            if (arr?.length > MAX_SESSION_COUNT) {
              return arr.slice(0, MAX_SESSION_COUNT)
            } 
            return arr
        })
        return id;
    }

    const beforeUpload = () => {
        if (fileList.length >= 5) {
            return Upload.LIST_IGNORE
        } 
        return true
    }

    const handleChange: UploadProps['onChange'] = (info) => {
        let newFileList = [...fileList, ...info.fileList];

        newFileList = newFileList.map((file) => {
            if (file.response) {
                file.url = file.response.url;
            }
            return file;
        });

        setFileList(newFileList);
    };
    
    const addMessage = (id: string, messages: Message[]) => {
        setSessionMessages(prev => ({
            ...prev,
            [id]: [...messages]
        }))
        sessionAPI.setMessagesBySessionId(id, messages)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!input.trim() || isProcessing) return;
    
        const currentFileUrls = fileList?.filter((file) => !!file?.url && file?.url !== '').map((file) => file.url!)
        setInput('');
        setFileList([]);
        setIsProcessing(true);
        setCurrentScript(null);
    
        let id = activeSessionId
        // 保存当前的session
        if (!id || id === '') {
          id = addNewSession(input)
        }
        // Add user message
        const messages: Message[] = [
            ...(sessionMessages[id] || []),
            { 
              type: 'user', 
              content: input, 
              timestamp: Date.now() 
            }
        ]
        addMessage(id, messages)
        try {
          // 1. Create Chat (backend will auto-select tools)
          const { chat_id } = await api.createChat(input, config, currentFileUrls);
    
          // 2. Connect WebSocket
          const ws = new WebSocket(api.getWebSocketUrl(chat_id));
    
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
    
            if (data.type === 'iteration_start') {
              messages.push({ 
                type: 'iteration', 
                content: `🔄 Starting iteration ${data.iteration}/${data.max_iterations}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              })
            } else if (data.type === 'iteration_end') {
              const statusEmoji = data.status === 'success' ? '✅' : data.status === 'failed' ? '❌' : '🔁';
              messages.push({
                type: 'iteration', 
                content: `${statusEmoji} Iteration ${data.iteration} ${data.status}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              })
            } else if (data.type === 'script') {
              setCurrentScript(data.content);
              messages.push({
                            type: 'system', 
                content: `📝 Generated script (iteration ${data.iteration})`, 
                timestamp: Date.now(),
                iteration: data.iteration
              })
            } else if (data.type === 'log') {
              messages.push({
                type: 'log', 
                content: `[${data.stream || 'LOG'}] ${data.content}`, 
                timestamp: Date.now() 
              })
            } else if (data.type === 'evaluation_result') {
              const emoji = data.meets_requirement ? '✅' : '⚠️';
              messages.push({
                type: 'evaluation', 
                content: `${emoji} Evaluation (iteration ${data.iteration}): ${data.meets_requirement ? 'PASS' : 'FAIL'} (confidence: ${(data.confidence_score * 100).toFixed(0)}%)\nReason: ${data.reason}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              })
            } else if (data.type === 'revision_advice') {
              messages.push({
                type: 'advice', 
                content: `💡 Revision advice (iteration ${data.iteration}):\n${data.advice.advice || JSON.stringify(data.advice, null, 2)}`, 
                timestamp: Date.now(),
                iteration: data.iteration
              })
            } else if (data.type === 'final_result') {
              // 最终结果 - 现在才关闭连接
              const emoji = data.status === 'success' ? '🎉' : '❌';
              messages.push({
                type: 'result', 
                content: `${emoji} Final result (${data.total_iterations} iterations): ${data.status}\n${data.result ? JSON.stringify(data.result, null, 2) : data.error || ''}`, 
                timestamp: Date.now() 
              })
              setIsProcessing(false);
              ws.close();
            } else if (data.type === 'result') {
              // 兼容旧的 result 消息（如果有的话）
              messages.push({
                type: 'result', 
                content: data.content, 
                timestamp: Date.now()
              })
            } else if (data.type === 'error') {
              messages.push({
                type: 'error', 
                content: data.content, 
                timestamp: Date.now()
              })
              setIsProcessing(false);
              ws.close();
            } else if (data.type === 'status') {
              messages.push({
                type: 'system', 
                content: data.content, 
                timestamp: Date.now()
              })
            }
            addMessage(id, messages)
          };
    
          ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            messages.push({
              type: 'error', 
              content: 'Connection error', 
              timestamp: Date.now()
            })
            addMessage(id, messages)
            setIsProcessing(false);
          };
    
        } catch (err) {
          console.error(err);
          messages.push({
            type: 'error', 
            content: 'Failed to start chat', 
            timestamp: Date.now()
          })
          addMessage(id, messages)
          setIsProcessing(false);
        }
    };

    return (
        <div className="flex flex-col bg-[#f9f9f9] w-full h-full overflow-x-hidden">
            <MessageList 
                messages={sessionMessages[activeSessionId]} 
                currentScript={currentScript} 
            />
            <div className="px-4 pb-4">
                {/* Uploaded Files */}
                <div className="flex flex-col bg-white rounded-xl border border-gray-200">
                    {fileList.length > 0 && (
                        <div className="flex flex-wrap p-1 gap-2 border-b border-gray-200">
                            {fileList.map((file, index) => (
                                <div
                                    key={index}
                                    className="bg-gray-50 text-primary-700 px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 cursor-pointer"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        window.open(file.url, '_blank')
                                    }}
                                >
                                    <span>{file.name}</span>
                                    {file?.size && <span className="text-[#ccc]">({(file.size / 1024 / 1024).toFixed(2)}MB)</span>}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setFileList(files => files.filter((_, i) => i !== index))
                                        }}
                                        className="hover:text-gray-900 font-bold"
                                    >
                                        <Trash2 className="w-4 h-4"/>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    {/* Input Box */}
                    <div className="flex h-[100px] items-center gap-2 focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all px-2">
                        <Upload
                            fileList={[]}
                            action={'http://localhost:8001/api/upload'}
                            onChange={handleChange}
                            beforeUpload={beforeUpload}
                            multiple
                            disabled={isProcessing}
                        >
                            <button 
                                className="p-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
                                disabled={isProcessing}
                            >
                                <Plus className="w-5 h-5 text-gray-600" />
                            </button>
                        </Upload>
                        
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey && !isProcessing) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                            placeholder="输入消息...（支持文本和文件）"
                            className="flex-1 h-full resize-none bg-transparent px-2 py-2 focus:outline-none text-gray-800 placeholder-gray-400"
                            rows={1}
                            disabled={isProcessing}
                        />
                        
                        <button
                            onClick={handleSubmit}
                            disabled={isProcessing || (!input.trim() && fileList.length === 0)}
                            className="p-2.5 bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 disabled:bg-[rgba(0,0,0,0.04)] disabled:cursor-not-allowed transition-colors flex-shrink-0"
                        >
                            {isProcessing ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                            <Send className="w-5 h-5" />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Chat;