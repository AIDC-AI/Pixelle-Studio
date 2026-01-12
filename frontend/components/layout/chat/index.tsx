'use client'

import { Message, ExecutionResult, OutputFile, ToolCallInfo, ToolResultInfo } from "@/types/message";
import { useEffect, useState, useRef, useCallback } from "react";
import MessageList from "./messageList";
import { UploadFile } from "antd";
import { api } from "@/lib/api";
import { useApp } from "@/context";
import { sessionAPI } from "@/lib/sessionApi";
import LeftPanel from "../leftPanel";
import SkillEditor from "../skillEditor";
import Input from "./input";
import useChatStorage from "@/hooks/useChatStorage";

const Chat = () => {
    const { 
      user,
      activeSessionId, 
      setActiveSessionId,
      skillEditored
    } = useApp();

    const { 
      messages, 
      sessions, 
      saveMessages, 
      loadSessions, 
      createSession, 
      deleteSession,
      updateSessionBackendId
    } = useChatStorage(activeSessionId)

    const [isProcessing, setIsProcessing] = useState<boolean>(false);

    const [input, setInput] = useState<string>('');
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    
    // WebSocket 引用，用于停止推理
    const wsRef = useRef<WebSocket | null>(null);
    
    // 左侧面板宽度拖拽
    const [leftPanelWidth, setLeftPanelWidth] = useState<number>(256);
    const [isDragging, setIsDragging] = useState<boolean>(false);
    const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState<boolean>(false);
    const dragStartXRef = useRef<number>(0);
    const dragStartWidthRef = useRef<number>(256);

    const addNewSession = async (title: string) => {
        const session = await createSession(title)
        saveActiveSessionId(session.id)
        return session;
    }

    const handleDeleteSession = async (id: string) => {
      await deleteSession(id)
    }
    
    const addMessages = async (id: string, messages: Message[]) => {
      await saveMessages(id, messages)
    }

    const saveActiveSessionId = (id: string) => {
      setActiveSessionId(id)
      sessionAPI.setActiveSessionId(id)
    }
    
    // 停止推理
    const handleStop = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setIsProcessing(false);
    }, []);
    
    // 拖拽处理
    const handleDragStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
        dragStartXRef.current = e.clientX;
        dragStartWidthRef.current = leftPanelWidth;
    }, [leftPanelWidth]);
    
    const handleDragMove = useCallback((e: MouseEvent) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - dragStartXRef.current;
        const newWidth = Math.max(200, Math.min(500, dragStartWidthRef.current + deltaX));
        setLeftPanelWidth(newWidth);
    }, [isDragging]);
    
    const handleDragEnd = useCallback(() => {
        setIsDragging(false);
    }, []);
    
    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleDragMove);
            document.addEventListener('mouseup', handleDragEnd);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        }
        
        return () => {
            document.removeEventListener('mousemove', handleDragMove);
            document.removeEventListener('mouseup', handleDragEnd);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isDragging, handleDragMove, handleDragEnd]);

    const handleSubmit = async () => {
      if (!input.trim() || isProcessing || !user?.uid) return;
      
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
      
      // 找到当前session
      let session = sessions.find(s => s.id === activeSessionId)
      // 如果没有，新建一个
      if (!session) {
        session = await addNewSession(input)
      }
      
      const currentSession = session;
      const currentSessionId = currentSession.id;

      const backendSessionId = currentSession.backendSessionId

      // 保存当前message
      addMessages(currentSessionId, [{ 
        type: 'user', 
        content: input, 
        outputFiles,
        timestamp: Date.now() 
      }])
      
      let currentExecCount = 0;
      
      try {
        // 1. Create Chat (backend will auto-select tools)
        const { chat_id, session_id } = await api.createChat(
          input,
          user.uid,
          currentFileUrls,
          currentFileNames,
          backendSessionId
        );

        // Bind backend session id to this local session for future turns
        if (!backendSessionId && session_id) {
          await updateSessionBackendId(currentSessionId, session_id)
        }

        // 2. Connect WebSocket
        const ws = new WebSocket(api.getWebSocketUrl(chat_id));
        wsRef.current = ws;

        let lastToolCallName = ""
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          const _messages: Message[] = []

          if (data.type === 'iteration_start') {
            _messages.push({ 
              type: 'iteration', 
              content: `🔄 Starting iteration ${data.iteration}/${data.max_iterations}`, 
              timestamp: Date.now(),
              iteration: data.iteration
            })
          } else if (data.type === 'iteration_end') {
            const statusEmoji = data.status === 'success' ? '✅' : data.status === 'failed' ? '❌' : '🔁';
            _messages.push({
              type: 'iteration', 
              content: `${statusEmoji} Iteration ${data.iteration} ${data.status}`, 
              timestamp: Date.now(),
              iteration: data.iteration
            })
          } else if (data.type === 'script') {
            setCurrentScript(data.content);
            _messages.push({
              type: 'system', 
              content: `📝 Generated script (iteration ${data.iteration})`, 
              timestamp: Date.now(),
              iteration: data.iteration
            })
          } else if (data.type === 'code') {
            // Handle code generation event
            currentExecCount = data.execution_count || currentExecCount + 1;
            _messages.push({
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
            // Handle execution result event
            const outputFiles: OutputFile[] = data.output_files || [];
            const execResult: ExecutionResult = {
              status: data.status,
              stdout: data.stdout || '',
              stderr: data.stderr || '',
              result: data.result,
              output_files: outputFiles
            };
            _messages.push({
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
              _messages.push({
                type: 'output_files',
                content: `${outputFiles.length} 个文件已生成`,
                timestamp: Date.now(),
                outputFiles: outputFiles
              })
            }
          } else if (data.type === 'response') {
            // Handle direct response from agent
            _messages.push({
              type: 'response',
              content: data.content,
              timestamp: Date.now()
            })
            // Mark that we received a direct response
            // So we don't show duplicate content in final_result
            currentExecCount = -1; // Use -1 as a flag for direct response
          } else if (data.type === 'skill_loaded') {
            // Handle skill loaded event
            _messages.push({
              type: 'skill_loaded',
              content: data.skill_name,
              timestamp: Date.now(),
              skillName: data.skill_name
            })
          } else if (data.type === 'log') {
            _messages.push({
              type: 'log', 
              content: `[${data.stream || 'LOG'}] ${data.content}`, 
              timestamp: Date.now() 
            })
          } else if (data.type === 'evaluation_result') {
            const emoji = data.meets_requirement ? '✅' : '⚠️';
            _messages.push({
              type: 'evaluation', 
              content: `${emoji} Evaluation (iteration ${data.iteration}): ${data.meets_requirement ? 'PASS' : 'FAIL'} (confidence: ${(data.confidence_score * 100).toFixed(0)}%)\nReason: ${data.reason}`, 
              timestamp: Date.now(),
              iteration: data.iteration
            })
          } else if (data.type === 'revision_advice') {
            _messages.push({
              type: 'advice', 
              content: `💡 Revision advice (iteration ${data.iteration}):\n${data.advice.advice || JSON.stringify(data.advice, null, 2)}`, 
              timestamp: Date.now(),
              iteration: data.iteration
            })
          } else if (data.type === 'final_result') {
            // 最终结果 - 现在才关闭连接
            const hadDirectResponse = currentExecCount === -1;
            const hadCodeExecution = currentExecCount > 0;
            
            // Only show final result card if:
            // 1. There was code execution, OR
            // 2. There was an error, OR  
            // 3. No direct response was sent before
            if (hadCodeExecution || data.status === 'error' || data.status === 'failed' || !hadDirectResponse) {
              // For direct responses, the content is already shown, so skip it
              if (!hadDirectResponse || hadCodeExecution) {
                _messages.push({
                  type: 'result', 
                  content: data.result || data.error || '',
                  timestamp: Date.now()
                })
              }
            }
            setIsProcessing(false);
            wsRef.current = null;
            ws.close();
          } else if (data.type === 'result') {
            // 兼容旧的 result 消息（如果有的话）
            _messages.push({
              type: 'result', 
              content: data.content, 
              timestamp: Date.now()
            })
          } else if (data.type === 'error') {
            _messages.push({
              type: 'error', 
              content: data.content, 
              timestamp: Date.now()
            })
            setIsProcessing(false);
            wsRef.current = null;
            ws.close();
          } else if (data.type === 'status') {
            _messages.push({
              type: 'system', 
              content: data.content, 
              timestamp: Date.now()
            })
          } else if (data.type === 'tool_call') {
            // Handle tool call started event
            lastToolCallName = data.name
            const toolCall: ToolCallInfo = {
              name: data.name,
              arguments: data.arguments || {},
              call_id: data.call_id
            };
            _messages.push({
              type: 'tool_call',
              content: `🔧 Calling tool: ${data.name}`,
              timestamp: Date.now(),
              toolCall
            })
          } else if (data.type === 'tool_result') {
            // Handle tool result event
            let name = data.name
            // 如果name为unknown，使用之前记录的lastToolCallName
            if (name === 'unknown') {
              name = lastToolCallName
            }
            const toolResult: ToolResultInfo = {
              name,
              result: data.result,
              call_id: data.call_id
            };
            _messages.push({
              type: 'tool_result',
              content: data.result,
              timestamp: Date.now(),
              toolResult
            })
          } else if (data.type === 'response_delta') {
            // Skip streaming deltas - they're handled by accumulated response
            // Could implement streaming display here if needed
          }

          addMessages(currentSessionId, _messages)
        };

        ws.onerror = (err) => {
          console.error('WebSocket error:', err);
          addMessages(currentSessionId, [{
            type: 'error', 
            content: 'Connection error', 
            timestamp: Date.now()
          }])
          setIsProcessing(false);
          wsRef.current = null;
        };
        
        ws.onclose = () => {
          wsRef.current = null;
        };

      } catch (err) {
        console.error(err);
        addMessages(currentSessionId, [{
          type: 'error', 
          content: 'Failed to start chat', 
          timestamp: Date.now()
        }])
        setIsProcessing(false);
      }
    };

    useEffect(() => {
      (
        async () => {
          await loadSessions()
        } 
      )()
    }, [])

    return (
      <div className="w-screen h-screen flex overflow-hidden">
        {/* Left Panel with dynamic width */}
        <div style={{ width: isLeftPanelCollapsed ? 48 : leftPanelWidth, flexShrink: 0, transition: 'width 0.2s ease' }}>
          <LeftPanel 
            sessions={sessions} 
            handleDeleteSession={handleDeleteSession}
            isCollapsed={isLeftPanelCollapsed}
            onCollapsedChange={setIsLeftPanelCollapsed}
          />
        </div>
        
        {/* Resizer - 只在面板展开时显示 */}
        {!isLeftPanelCollapsed && (
          <div 
            className={`w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize transition-colors flex-shrink-0 ${isDragging ? 'bg-blue-500' : ''}`}
            onMouseDown={handleDragStart}
          />
        )}
        
        {/* Main Chat Area */}
        <div className="flex flex-col bg-gray-50 flex-1 h-full overflow-x-hidden">
            <MessageList 
                messages={messages} 
                currentScript={currentScript} 
                isProcessing={isProcessing}
            />
            <Input 
              isProcessing={isProcessing}
              input={input}
              setInput={setInput}
              fileList={fileList}
              setFileList={setFileList}
              handleSubmit={handleSubmit}
              onStop={handleStop}
            />
        </div>
        {
          skillEditored && <SkillEditor />
        }
      </div>
    );
};

export default Chat;
