'use client'

import { Message, ExecutionResult, OutputFile } from "@/types/message";
import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { useApp } from "@/context";
import { sessionAPI } from "@/lib/sessionApi";
import LeftPanel from "../leftPanel";
import SkillEditor from "../skillEditor";
import Input from "./input";
import useChatStorage from "@/hooks/useChatStorage";
import { useMCPServer } from "@/hooks/useMCPServer";
import FilePreview from "./filePreview";
import VirtualMessageList from "./virtualMessageList";
import { UploadFile } from "@/components/ui/upload";

const Chat = () => {
    const { 
      user,
      activeSessionId, 
      setActiveSessionId,
      skillEditored,
      setSkillEditored
    } = useApp();

    const { tools: mcpTools } = useMCPServer();

    const { 
      messages, 
      sessions, 
      saveMessages, 
      loadSessions, 
      createSession, 
      deleteSession,
      updateSessionBackendId,
      updateSessionTitle
    } = useChatStorage(activeSessionId)

    const [isProcessing, setIsProcessing] = useState<boolean>(false);

    const [input, setInput] = useState<string>('');
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [currentScript, setCurrentScript] = useState<string | null>(null);
    
    // 流式响应状态
    const [streamingResponse, setStreamingResponse] = useState<string>('');
    // 标记是否有工具调用（有工具调用时不应该流式输出）
    const hasToolCallsRef = useRef<boolean>(false);
    
    // 文件预览状态
    const [previewFile, setPreviewFile] = useState<OutputFile | null>(null);
    
    // WebSocket 引用，用于停止推理
    const wsRef = useRef<WebSocket | null>(null);
    
    // 左侧面板宽度
    const [leftPanelWidth, setLeftPanelWidth] = useState<number>(256);
    const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState<boolean>(false);
    
    // 预览面板宽度百分比
    const [previewWidthPercent, setPreviewWidthPercent] = useState<number>(50);
    
    // 拖拽状态使用 ref，避免闭包问题
    const dragStateRef = useRef<{
        isDragging: 'left' | 'preview' | null;
        startX: number;
        startValue: number;
    }>({ isDragging: null, startX: 0, startValue: 0 });
    
    // 容器 ref
    const containerRef = useRef<HTMLDivElement>(null);
    
    // 强制更新用于拖拽视觉反馈
    const [, forceUpdate] = useState({});

    // 检查文件是否可预览
    const canPreviewFile = (filename: string): boolean => {
        const ext = filename.split('.').pop()?.toLowerCase() || '';
        return ['html', 'htm', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'txt', 'md'].includes(ext);
    };

    // 自动预览可预览的文件
    const autoPreviewFile = (files: OutputFile[]) => {
        // 优先预览 HTML 文件
        const htmlFile = files.find(f => {
            const ext = f.file_name.split('.').pop()?.toLowerCase() || '';
            return ['html', 'htm'].includes(ext);
        });
        if (htmlFile) {
            setPreviewFile(htmlFile);
            return;
        }
        
        // 其次预览图片
        const imageFile = files.find(f => {
            const ext = f.file_name.split('.').pop()?.toLowerCase() || '';
            return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
        });
        if (imageFile) {
            setPreviewFile(imageFile);
            return;
        }
        
        // 最后预览 PDF 或文本
        const otherFile = files.find(f => canPreviewFile(f.file_name));
        if (otherFile) {
            setPreviewFile(otherFile);
        }
    };

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
    
    // 统一的拖拽处理
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            const state = dragStateRef.current;
            if (!state.isDragging) return;
            
            e.preventDefault();
            
            if (state.isDragging === 'left') {
                const deltaX = e.clientX - state.startX;
                const newWidth = Math.max(200, Math.min(500, state.startValue + deltaX));
                setLeftPanelWidth(newWidth);
            } else if (state.isDragging === 'preview' && containerRef.current) {
                const containerWidth = containerRef.current.offsetWidth;
                if (containerWidth > 0) {
                    const deltaX = state.startX - e.clientX;
                    const deltaPercent = (deltaX / containerWidth) * 100;
                    const newPercent = Math.max(25, Math.min(75, state.startValue + deltaPercent));
                    setPreviewWidthPercent(newPercent);
                }
            }
        };
        
        const handleMouseUp = () => {
            if (dragStateRef.current.isDragging) {
                dragStateRef.current.isDragging = null;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                forceUpdate({});
            }
        };
        
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);
    
    // 开始左侧面板拖拽
    const handleLeftDragStart = (e: React.MouseEvent) => {
        e.preventDefault();
        dragStateRef.current = {
            isDragging: 'left',
            startX: e.clientX,
            startValue: leftPanelWidth
        };
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        forceUpdate({});
    };
    
    // 开始预览面板拖拽
    const handlePreviewDragStart = (e: React.MouseEvent) => {
        e.preventDefault();
        dragStateRef.current = {
            isDragging: 'preview',
            startX: e.clientX,
            startValue: previewWidthPercent
        };
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        forceUpdate({});
    };

    const handleSubmit = async () => {
      console.log('[DEBUG] handleSubmit called, input:', input, 'isProcessing:', isProcessing, 'user:', user);
      if (!input.trim() || isProcessing || !user?.uid) {
        console.log('[DEBUG] handleSubmit blocked: input empty?', !input.trim(), 'isProcessing?', isProcessing, 'no user.uid?', !user?.uid);
        return;
      }
      
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
      setStreamingResponse('');
      hasToolCallsRef.current = false;
      
      // 找到当前session
      let currentSession = sessions.find(s => s.id === activeSessionId)
      // 如果没有，新建一个
      if (!currentSession) {
        currentSession = await addNewSession(input)
        
        // 异步生成标题（不阻塞主流程）
        api.generateTitle(input).then(({ title }) => {
          if (title && title.length <= 10) {
            updateSessionTitle(currentSession!.id, title);
          } else if (title && title.length > 10) {
            updateSessionTitle(currentSession!.id, title.substring(0, 10));
          }
        }).catch((err) => {
          console.error('Failed to generate title:', err);
          // 使用input的前10个字符作为fallback
          const fallbackTitle = input.substring(0, 10);
          updateSessionTitle(currentSession!.id, fallbackTitle);
        });
      }
      const currentSessionId = currentSession.id;
      const backendSessionId = currentSession.backendSessionId;
      
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
        
        // 立即显示"任务执行中"的状态提示（使用streamingResponse）
        setStreamingResponse('任务执行中，等待响应...');

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          const _messages: Message[] = []

          if (data.type === 'response_delta') {
            // 只有在没有工具调用的情况下才累积流式输出
            // 后端已经过滤掉了<execute>标签内的内容，这里做二次检查（快速回撤）
            if (!hasToolCallsRef.current) {
              const deltaContent = data.content || '';
              
              // 使用函数式更新确保总是使用最新的状态值
              setStreamingResponse(prev => {
                // 如果当前是"任务执行中..."的提示，收到第一个真实响应时替换掉它
                const isLoadingText = prev.includes('任务执行中');
                const newContent = isLoadingText ? deltaContent : (prev + deltaContent);
                const trimmedContent = newContent.trim();
                
                // 前端快速回撤：检测到不该显示的内容，立即清空
                if (trimmedContent.includes('{"code') || 
                    trimmedContent.includes('{ "code') || 
                    trimmedContent.includes('{\'code') ||
                    trimmedContent.includes('<execute')) {
                  // 立即清空并标记
                  hasToolCallsRef.current = true;
                  console.log('[Frontend] Detected tool call pattern, rolling back streaming content');
                  return '';
                } else if (trimmedContent === '{' || trimmedContent === '{"') {
                  // 单独的 { 或 {" 也可疑，但不立即清空，而是等待下一个字符
                  return newContent;
                } else {
                  // 安全内容，正常显示
                  return newContent;
                }
              });
            }
            // 不添加到messages中，让MessageList实时显示streamingResponse
          } else if (data.type === 'iteration_start') {
            // 清除"任务执行中..."提示
            setStreamingResponse('');
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
              
              // 自动预览可预览的文件
              autoPreviewFile(outputFiles);
            }
            
            // 代码执行完成后，重置工具调用标记，允许后续的流式输出
            hasToolCallsRef.current = false;
          } else if (data.type === 'response') {
            // Handle direct response from agent (完整响应，非流式)
            // 如果有流式内容累积，使用累积的内容；否则使用data.content
            const finalContent = streamingResponse || data.content;
            if (finalContent) {
              _messages.push({
                type: 'response',
                content: finalContent,
                timestamp: Date.now()
              })
            }
            // 清空流式响应
            setStreamingResponse('');
            // Mark that we received a direct response
            // So we don't show duplicate content in final_result
            currentExecCount = -1; // Use -1 as a flag for direct response
          } else if (data.type === 'tool_call') {
            // 标记有工具调用，停止流式输出
            hasToolCallsRef.current = true;
            // 清除"任务执行中..."提示
            setStreamingResponse('');
            
            // Handle tool call event
            const toolName = data.name || '';
            
            // 特殊处理 execute_code: 直接显示代码而不是工具调用
            if (toolName === 'execute_code' && data.arguments && data.arguments.code) {
              currentExecCount = currentExecCount + 1;
              _messages.push({
                type: 'code',
                content: data.arguments.code,
                timestamp: Date.now(),
                codeData: {
                  code: data.arguments.code,
                  executionCount: currentExecCount,
                  reasoning: undefined
                }
              });
            } else {
              // 其他工具正常显示工具调用
              _messages.push({
                type: 'tool_call',
                content: toolName,
                timestamp: Date.now(),
                toolCall: {
                  name: toolName,
                  arguments: data.arguments,
                  call_id: data.call_id
                }
              });
            }
          } else if (data.type === 'tool_result') {
            // Handle tool result event
            // 跳过以下情况：
            // 1. execute_code 的结果（会有单独的 execution_result 事件）
            // 2. 名称为 'unknown' 的结果（通常是内部错误或未正确识别的工具）
            if (data.name !== 'execute_code' && data.name !== 'unknown') {
              _messages.push({
                type: 'tool_result',
                content: typeof data.result === 'string' ? data.result : JSON.stringify(data.result),
                timestamp: Date.now(),
                toolResult: {
                  name: data.name,
                  result: data.result,
                  call_id: data.call_id
                }
              });
            }
          } else if (data.type === 'skill_loaded') {
            // Handle skill loaded event
            _messages.push({
              type: 'skill_loaded',
              content: data.skill_name,
              timestamp: Date.now(),
              skillName: data.skill_name
            })
          } else if (data.type === 'thinking') {
            // 清除"任务执行中..."提示
            setStreamingResponse('');
            // Handle thinking process from LLM
            _messages.push({
              type: 'thinking',
              content: data.content || data.thinking,
              timestamp: Date.now()
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
            
            // 如果有未完成的流式响应，先保存它
            if (streamingResponse) {
              _messages.push({
                type: 'response',
                content: streamingResponse,
                timestamp: Date.now()
              });
            }
            
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
            
            // 清空流式响应
            setStreamingResponse('');
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
          console.log('WebSocket closed');
          setIsProcessing(false);
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
    
    const isLeftDragging = dragStateRef.current.isDragging === 'left';
    const isPreviewDragging = dragStateRef.current.isDragging === 'preview';

    return (
      <div className="w-screen h-screen flex overflow-hidden">
        {/* Left Panel with dynamic width */}
        <div 
          className="shrink-0 h-full"
          style={{ 
            width: isLeftPanelCollapsed ? 48 : leftPanelWidth,
            transition: isLeftDragging ? 'none' : 'width 0.15s ease-out'
          }}
        >
          <LeftPanel 
            sessions={sessions} 
            handleDeleteSession={handleDeleteSession}
            isCollapsed={isLeftPanelCollapsed}
            onCollapsedChange={setIsLeftPanelCollapsed}
          />
        </div>
        
        {/* Left Panel Resizer */}
        {!isLeftPanelCollapsed && (
          <div 
            className={`w-1.5 cursor-col-resize shrink-0 transition-colors ${
              isLeftDragging ? 'bg-blue-500' : 'bg-gray-200 hover:bg-blue-400'
            }`}
            onMouseDown={handleLeftDragStart}
            style={{ touchAction: 'none' }}
          />
        )}
        
        {/* Main Content Area (Chat + Preview) */}
        <div ref={containerRef} className="flex flex-1 h-full overflow-hidden min-w-0">
          {/* Chat Area */}
          <div 
            className="flex flex-col bg-gray-50 h-full overflow-hidden shrink-0"
            style={{ 
              width: previewFile ? `${100 - previewWidthPercent}%` : '100%',
              transition: isPreviewDragging ? 'none' : 'width 0.15s ease-out'
            }}
          >
              <VirtualMessageList 
                  messages={messages} 
                  currentScript={currentScript}
                  onFilePreview={setPreviewFile}
                  streamingResponse={streamingResponse}
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
          
          {/* Preview Panel with Resizer */}
          {previewFile && (
            <>
              {/* Preview Resizer */}
              <div 
                className={`w-1.5 cursor-col-resize shrink-0 transition-colors ${
                  isPreviewDragging ? 'bg-orange-500' : 'bg-gray-200 hover:bg-orange-400'
                }`}
                onMouseDown={handlePreviewDragStart}
                style={{ touchAction: 'none' }}
              />
              
              {/* Preview Panel */}
              <div 
                className="h-full overflow-hidden shrink-0"
                style={{ 
                  width: `${previewWidthPercent}%`,
                  transition: isPreviewDragging ? 'none' : 'width 0.15s ease-out'
                }}
              >
                <FilePreview 
                  file={previewFile}
                  onClose={() => setPreviewFile(null)}
                />
              </div>
            </>
          )}
        </div>
        
        {skillEditored && <SkillEditor />}
      </div>
    );
};

export default Chat;
