'use client'

import { Message, ExecutionResult, OutputFile } from "@/types/message";
import { useState } from "react";
import MessageList from "./messageList";
import { Upload, UploadFile, UploadProps } from "antd";
import { api, API_BASE } from "@/lib/api";
import { useApp } from "@/context";
import { MAX_SESSION_COUNT, sessionAPI } from "@/lib/session";
import { Loader2, Plus, Send, Trash2 } from "lucide-react";

const Chat = () => {
    const { 
      activeSessionId, 
      setActiveSessionId,
      sessions,
      setSessions,
      sessionMessages,
      setSessionMessages
    } = useApp();
    
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    const [input, setInput] = useState<string>('');
    
    // Track execution count for code/result pairing
    const [executionCount, setExecutionCount] = useState<number>(0);
    
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
        // info.fileList 已经是完整的文件列表，不需要再追加
        let newFileList = info.fileList.map((file) => {
            if (file.response) {
                file.url = file.response.url;
                // 存储本地文件路径，供 Agent 直接使用
                (file as any).filePath = file.response.file_path;
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
        
        // 检查是否有文件正在上传
        const uploadingFiles = fileList.filter(f => f.status === 'uploading');
        if (uploadingFiles.length > 0) {
            console.log('[DEBUG] 等待文件上传完成...');
            return; // 阻止提交，等待上传完成
        }
    
        // 只选择已上传完成的文件 (status === 'done')
        const doneFiles = fileList.filter(f => f.status === 'done');
        
        // 直接从 response 中获取，确保数据正确
        const currentFileUrls = doneFiles
            ?.filter((file) => !!(file?.response?.url || file?.url))
            .map((file) => (file.response?.url || file.url) as string)
        const currentFileNames = doneFiles
            ?.filter((file) => !!file?.response?.file_name)
            .map((file) => file.response.file_name as string)
        const outputFiles = doneFiles
            ?.filter((file) => !!(file?.response?.url || file?.url) && (file?.name))
            .map((file) => ({
              file_name: file?.name,
              file_url: file?.response?.url || file?.url,
              file_size: file.size || 0
            }))
            
        console.log('[DEBUG] doneFiles:', doneFiles.length, 'currentFileNames:', currentFileNames);
        setInput('');
        setFileList([]);
        setIsProcessing(true);
        setCurrentScript(null);
        setExecutionCount(0);
    
        let id = activeSessionId
        // 保存当前的session
        if (!id || id === '') {
          id = addNewSession(input)
        }

        // Lookup backend session id bound to this local session (Cursor-like)
        const currentSession = sessions.find(s => s.id === id)
        const backendSessionId = currentSession?.backendSessionId
        // Add user message
        const messages: Message[] = [
            ...(sessionMessages[id] || []),
            { 
              type: 'user', 
              content: input, 
              outputFiles,
              timestamp: Date.now() 
            }
        ]
        addMessage(id, messages)
        
        let currentExecCount = 0;
        
        try {
          // 1. Create Chat (backend will auto-select tools)
          const { chat_id, session_id } = await api.createChat(
            input,
            {},
            currentFileUrls,
            currentFileNames,
            backendSessionId
          );

          // Bind backend session id to this local session for future turns
          if (!backendSessionId && session_id) {
            setSessions(prev => prev.map(s => s.id === id ? { ...s, backendSessionId: session_id } : s))
          }
    
          // 2. Connect WebSocket
          const ws = new WebSocket(api.getWebSocketUrl(chat_id));
    
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
    
            // Remove "Processing your request..." message when we get first real response
            const removeProcessingMessage = () => {
              const processingIndex = messages.findIndex(m => 
                m.type === 'system' && m.content === 'Processing your request...'
              );
              if (processingIndex !== -1) {
                messages.splice(processingIndex, 1);
              }
            };
    
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
            } else if (data.type === 'code') {
              // NEW: Handle code generation event
              removeProcessingMessage(); // Remove loading message
              currentExecCount = data.execution_count || currentExecCount + 1;
              setExecutionCount(currentExecCount);
              messages.push({
                type: 'code',
                content: data.content,
                timestamp: Date.now(),
                codeData: {
                  code: data.content,
                  executionCount: currentExecCount,
                  reasoning: data.reasoning
                }
              })
            } else if (data.type === 'execution_result') {
              // NEW: Handle execution result event
              const outputFiles: OutputFile[] = data.output_files || [];
              const execResult: ExecutionResult = {
                status: data.status,
                stdout: data.stdout || '',
                stderr: data.stderr || '',
                result: data.result,
                output_files: outputFiles
              };
              messages.push({
                type: 'execution_result',
                content: execResult,
                timestamp: Date.now(),
                executionResult: execResult,
                codeData: {
                  code: '',
                  executionCount: currentExecCount
                }
              })
              
              // If there are output files, add a separate output_files message
              if (outputFiles.length > 0) {
                messages.push({
                  type: 'output_files',
                  content: `${outputFiles.length} 个文件已生成`,
                  timestamp: Date.now(),
                  outputFiles: outputFiles
                })
              }
            } else if (data.type === 'response') {
              // NEW: Handle direct response from agent
              removeProcessingMessage(); // Remove loading message
              messages.push({
                type: 'response',
                content: data.content,
                timestamp: Date.now()
              })
              // Mark that we received a direct response
              // So we don't show duplicate content in final_result
              currentExecCount = -1; // Use -1 as a flag for direct response
            } else if (data.type === 'skill_loaded') {
              // NEW: Handle skill loaded event
              messages.push({
                type: 'skill_loaded',
                content: data.skill_name,
                timestamp: Date.now(),
                skillName: data.skill_name
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
              removeProcessingMessage(); // Remove loading message
              // Skip adding final_result message if it's just a direct response (no code execution)
              // currentExecCount === -1 means we had a direct response
              // currentExecCount === 0 means no code was executed
              const hadDirectResponse = currentExecCount === -1;
              const hadCodeExecution = currentExecCount > 0;
              
              // Only show final result card if:
              // 1. There was code execution, OR
              // 2. There was an error, OR  
              // 3. No direct response was sent before
              if (hadCodeExecution || data.status === 'error' || data.status === 'failed' || !hadDirectResponse) {
                // For direct responses, the content is already shown, so skip it
                if (!hadDirectResponse || hadCodeExecution) {
                  messages.push({
                    type: 'result', 
                    content: data.result || data.error || '',
                    timestamp: Date.now()
                  })
                }
              }
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
              removeProcessingMessage(); // Remove loading message
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
        <div className="flex flex-col bg-linear-to-br from-slate-50 to-slate-100 w-full h-full overflow-x-hidden">
            <MessageList 
                messages={sessionMessages[activeSessionId]} 
                currentScript={currentScript} 
            />
            <div className="px-4 pb-4">
                {/* Uploaded Files */}
                <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-lg shadow-slate-200/50">
                    {fileList.length > 0 && (
                        <div className="flex flex-wrap p-2 gap-2 border-b border-slate-100">
                            {fileList.map((file, index) => (
                                <div
                                    key={index}
                                    className="bg-linear-to-r from-blue-50 to-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 cursor-pointer border border-indigo-100 hover:border-indigo-200 transition-colors"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        window.open(file.url, '_blank')
                                    }}
                                >
                                    <span className="font-medium">{file.name}</span>
                                    {file?.size && <span className="text-indigo-400 text-xs">({(file.size / 1024 / 1024).toFixed(2)}MB)</span>}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setFileList(files => files.filter((_, i) => i !== index))
                                        }}
                                        className="hover:text-red-500 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4"/>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    {/* Input Box */}
                    <div className="flex h-[100px] items-center gap-2 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100 transition-all px-3 rounded-2xl">
                        <Upload
                            fileList={fileList}
                            action={`${API_BASE}/upload`}
                            onChange={handleChange}
                            beforeUpload={beforeUpload}
                            showUploadList={false}
                            multiple
                            disabled={isProcessing}
                        >
                            <button 
                                className="p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors flex-shrink-0 border border-slate-200"
                                disabled={isProcessing}
                            >
                                <Plus className="w-5 h-5 text-slate-500" />
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
                            className="flex-1 h-full resize-none bg-transparent px-3 py-3 focus:outline-none text-slate-800 placeholder-slate-400"
                            rows={1}
                            disabled={isProcessing}
                        />
                        
                        <button
                            onClick={handleSubmit}
                            disabled={isProcessing || (!input.trim() && fileList.length === 0) || fileList.some(f => f.status === 'uploading')}
                            className="p-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:from-slate-200 disabled:to-slate-300 disabled:text-slate-400 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-lg shadow-blue-500/25 disabled:shadow-none"
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
