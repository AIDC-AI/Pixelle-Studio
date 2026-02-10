'use client'

import { Message, ExecutionResult, OutputFile } from "@/types/message";
import { useEffect, useState, useRef, useCallback, lazy, Suspense, useMemo } from "react";
import { api } from "@/lib/api";
import { useApp } from "@/context";
import { sessionAPI } from "@/lib/sessionApi";
import { chatStorage } from "@/lib/chatStorage";
import Input from "./input";
import useChatStorage from "@/hooks/useChatStorage";
import { UploadFile } from "@/components/ui/upload";
import { canPreviewFile } from "@/utils/utils";
import { DEFAULT_LEFT_PANEL_WIDTH, DEFAULT_PREVIEW_WIDTH_PERCENT, MAX_LEFT_PANEL_WIDTH, MAX_PREVIEW_WIDTH_PERCENT, MIN_LEFT_PANEL_WIDTH, MIN_PREVIEW_WIDTH_PERCENT } from "@/utils/data";
import { createParserState, filterCodeBlocks } from '@/utils/codeBlockFilter';
import User from "@/components/ui/user";
import LogoutButton from "@/components/ui/logoutButton";

// Dynamically import large components
const LeftPanel = lazy(() => import("../leftPanel"));
const MessageList = lazy(() => import("./messageList"));
const FilePreview = lazy(() => import("./filePreview"));

// Loading placeholder component
const LoadingPlaceholder = () => (
  <div className="flex items-center justify-center h-full">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
  </div>
);

const Chat = () => {
  const {
    user,
    activeSessionId,
    setActiveSessionId,
    // skillEditored
  } = useApp();

  const {
    messages,
    sessions,
    saveMessages,
    loadSessions,
    createSession,
    deleteSession,
    getSessionById,
    updateSessionBackendId,
    updateSessionTitle,
    messagesLoading
  } = useChatStorage(activeSessionId)

  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const [input, setInput] = useState<string>('');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [currentScript, setCurrentScript] = useState<string | null>(null);

  // Streaming response state
  const [streamingResponse, setStreamingResponse] = useState<string>('');
  // Flag whether there are tool calls (should not stream output when there are tool calls)
  const hasToolCallsRef = useRef<boolean>(false);

  // File preview state
  const [previewFile, setPreviewFile] = useState<OutputFile | null>(null);

  // WebSocket reference, used to stop inference
  const wsRef = useRef<WebSocket | null>(null);

  // Left panel width
  const [leftPanelWidth, setLeftPanelWidth] = useState<number>(DEFAULT_LEFT_PANEL_WIDTH);
  const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState<boolean>(false);

  // Preview panel width percentage
  const [previewWidthPercent, setPreviewWidthPercent] = useState<number>(DEFAULT_PREVIEW_WIDTH_PERCENT);

  // Filtered streaming response data
  const [parserState, setParserState] = useState(createParserState());

  // Drag state uses ref to avoid closure issues
  const dragStateRef = useRef<{
    isDragging: 'left' | 'preview' | null;
    startX: number;
    startValue: number;
  }>({ isDragging: null, startX: 0, startValue: 0 });

  // Container ref
  const containerRef = useRef<HTMLDivElement>(null);

  // Force update for drag visual feedback
  const [, forceUpdate] = useState({});

  // Auto-preview previewable files
  const autoPreviewFile = (files: OutputFile[]) => {
    // Prioritize previewing HTML files
    const htmlFile = files.find(f => {
      const ext = f.file_name.split('.').pop()?.toLowerCase() || '';
      return ['html', 'htm'].includes(ext);
    });
    if (htmlFile) {
      setPreviewFile(htmlFile);
      return;
    }

    // Then preview images
    const imageFile = files.find(f => {
      const ext = f.file_name.split('.').pop()?.toLowerCase() || '';
      return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
    });
    if (imageFile) {
      setPreviewFile(imageFile);
      return;
    }

    // Finally preview PDF or text
    const otherFile = files.find(f => canPreviewFile(f.file_name));
    if (otherFile) {
      setPreviewFile(otherFile);
    }
  };

  const handleNewSession = async (title: string) => {
    const session = await createSession(title)
    saveActiveSessionId(session.id)
    return session;
  }

  const handleChangeSession = (id: string) => {
    setPreviewFile(null)
    setTimeout(() => {
      setActiveSessionId(id)
    }, 0)
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

  // Stop inference
  const handleStop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsProcessing(false);
    // Reset parser state
    setParserState(createParserState());
  }, []);

  // Unified drag handling
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const state = dragStateRef.current;
      if (!state.isDragging) return;

      e.preventDefault();

      if (state.isDragging === 'left') {
        const deltaX = e.clientX - state.startX;
        const newWidth = Math.max(MIN_LEFT_PANEL_WIDTH, Math.min(MAX_LEFT_PANEL_WIDTH, state.startValue + deltaX));
        setLeftPanelWidth(newWidth);
      } else if (state.isDragging === 'preview' && containerRef.current) {
        const containerWidth = containerRef.current.offsetWidth;
        if (containerWidth > 0) {
          const deltaX = state.startX - e.clientX;
          const deltaPercent = (deltaX / containerWidth) * 100;
          const newPercent = Math.max(MIN_PREVIEW_WIDTH_PERCENT, Math.min(MAX_PREVIEW_WIDTH_PERCENT, state.startValue + deltaPercent));
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

  // Start left panel drag
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

  // Start preview panel drag
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

    // Check if any files are still uploading
    const uploadingFiles = fileList.filter(f => f.status === 'uploading');
    if (uploadingFiles.length > 0) {
      console.log('[DEBUG] Waiting for file upload to complete...');
      return; // Block submission, wait for upload to complete
    }

    // Only select files that have finished uploading (status === 'done')
    const doneFiles = fileList.filter(f => f.status === 'done');

    // Get directly from response to ensure data correctness
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
    setParserState(createParserState()); // Reset parser state
    hasToolCallsRef.current = false;

    // Find current session
    let session = sessions.find(s => s.id === activeSessionId)
    // If not found, create a new one
    if (!session) {
      session = await handleNewSession(input)

      // Async title generation (non-blocking)
      api.generateTitle(input).then(({ title }) => {
        if (title) {
          // Backend already constrains title to 50 chars; just use it directly
          updateSessionTitle(session!.id, title.trim());
        }
      }).catch((err) => {
        console.error('Failed to generate title:', err);
        // Use first 20 characters of input as fallback
        const fallbackTitle = input.length > 20 ? input.substring(0, 20) + '...' : input;
        updateSessionTitle(session!.id, fallbackTitle);
      });
    }
    const currentSessionId = session.id;
    const backendSessionId = session.backendSessionId;

    // Save current message
    addMessages(currentSessionId, [{
      type: 'user',
      content: input,
      outputFiles,
      timestamp: Date.now()
    }])

    let currentExecCount = 0;
    let receivedFinalResult = false;

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

      // Immediately show "task in progress" status hint (using streamingResponse)
      setStreamingResponse('Task in progress, waiting for response...');

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const _messages: Message[] = []

        if (data.type === 'response_delta') {
          const deltaContent = data.accumulated || '';
          // Filter code blocks from the content
          const { filtered, state: newParserState } = filterCodeBlocks(deltaContent.trim(), parserState);
          setParserState(newParserState);
          // Update state - show filtered reasoning text
          setStreamingResponse(filtered);
          // setStreamingResponse(prev => {
          //   // const newContent = prev + filtered;
          //   // const trimmedContent = newContent.trim();
          //   // console.log('prev--->', prev);
          //   // console.log('filtered2--->', filtered);
          //   // If this is the first real response after "Processing..." message
          //   const isLoadingText = prev.includes('Task in progress');
          //   return isLoadingText ? filtered : filtered;
          // });
          // Only accumulate streaming output when there are no tool calls
          // Backend has already filtered content within <execute> tags, this is a secondary check (quick rollback)
          // if (!hasToolCallsRef.current) {
          //   const deltaContent = data.content || '';

          //   // Use functional update to always use the latest state value
          //   setStreamingResponse(prev => {
          //     // If current is "task in progress..." hint, replace it when receiving the first real response
          //     const isLoadingText = prev.includes('Task in progress');
          //     const newContent = isLoadingText ? deltaContent : (prev + deltaContent);
          //     const trimmedContent = newContent.trim();
          //     return newContent;
          //     // Frontend quick rollback: clear immediately when detecting content that shouldn't be displayed
          //     if (trimmedContent.includes('{"code') ||
          //       trimmedContent.includes('{ "code') ||
          //       trimmedContent.includes('{\'code') ||
          //       trimmedContent.includes('<execute')) {
          //       // Clear immediately and mark
          //       hasToolCallsRef.current = true;
          //       console.log('[Frontend] Detected tool call pattern, rolling back streaming content');
          //       return '';
          //     } else if (trimmedContent === '{' || trimmedContent === '{"') {
          //       // Standalone { or {" is also suspicious, but don't clear immediately, wait for next character
          //       return newContent;
          //     } else {
          //       // Safe content, display normally
          //       return newContent;
          //     }
          //   });
          // }
          // Don't add to messages, let MessageList display streamingResponse in real-time
        } else if (data.type === 'iteration_start') {
          // Clear "task in progress..." hint
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
          // === Before showing code, save accumulated reasoning text ===
          if (streamingResponse && streamingResponse.trim()) {
            _messages.push({
              type: 'response',
              content: streamingResponse.trim(),
              timestamp: Date.now()
            });
          }
          setStreamingResponse('');
          hasToolCallsRef.current = true;
          
          // Handle code generation event
          currentExecCount = data.execution_count || currentExecCount + 1;
          _messages.push({
            type: 'code',
            content: data.code || data.content,
            timestamp: Date.now(),
            codeData: {
              code: data.code || data.content,
              executionCount: currentExecCount,
              reasoning: data.reasoning
            }
          })
        } else if (data.type === 'file_created') {
          // ✅ Handle file creation event (from shell_exec or write_file)
          const filePath = data.path || '';
          const relativePath = data.relative_path || data.actual_filename || '';
          const fileSize = data.size || 0;
          const fileName = relativePath || filePath.split('/').pop() || 'file';

          // Convert file path to HTTP URL
          // /Users/.../backend/scripts/1/2026-02-04/test.pdf -> /files/1/2026-02-04/test.pdf
          let fileUrl = '';
          const scriptsMatch = filePath.match(/scripts\/(.+)$/);
          if (scriptsMatch) {
            fileUrl = `http://localhost:8001/files/${scriptsMatch[1]}`;
          } else {
            // If path format doesn't match, try using relative_path directly
            fileUrl = `http://localhost:8001/files/${relativePath}`;
          }

          // Create OutputFile object
          const outputFile: OutputFile = {
            file_name: fileName,
            file_url: fileUrl,
            file_size: fileSize
          };

          // Add to message list
          _messages.push({
            type: 'output_files',
            content: `File created: ${fileName}`,
            timestamp: Date.now(),
            outputFiles: [outputFile]
          });

          // Auto-preview previewable files
          autoPreviewFile([outputFile]);
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
              content: `${outputFiles.length} file(s) generated`,
              timestamp: Date.now(),
              outputFiles: outputFiles
            })

            // Auto-preview previewable files
            autoPreviewFile(outputFiles);
          }

          // After code execution completes, reset tool call flag to allow subsequent streaming output
          hasToolCallsRef.current = false;
          // Reset parser state, prepare to receive new reasoning text
          setParserState(createParserState());
        } else if (data.type === 'response') {
          // Handle direct response from agent (complete response, non-streaming)
          // If there is accumulated streaming content, use it; otherwise use data.content
          const finalContent = streamingResponse || data.content;
          if (finalContent) {
            _messages.push({
              type: 'response',
              content: finalContent,
              timestamp: Date.now()
            })
          }
          // Clear streaming response
          setStreamingResponse('');
          // Mark that we received a direct response
          // So we don't show duplicate content in final_result
          currentExecCount = -1; // Use -1 as a flag for direct response
        } else if (data.type === 'tool_call') {
          // Mark tool call, stop streaming output
          hasToolCallsRef.current = true;
          
          // === Critical fix: save accumulated reasoning text before clearing streaming response ===
          if (streamingResponse && streamingResponse.trim()) {
            _messages.push({
              type: 'response',
              content: streamingResponse.trim(),
              timestamp: Date.now()
            });
          }
          // Clear streaming response
          setStreamingResponse('');

          // Handle tool call event
          const toolName = data.name || '';

          // Special handling for execute_code: display code directly instead of tool call
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
            // Other tools display tool call normally
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
          // Skip the following cases:
          // 1. Results of execute_code (will have a separate execution_result event)
          // 2. Results with name 'unknown' (usually internal errors or unrecognized tools)
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
          // Clear "Task in progress..." message
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
          // Final result - close connection now
          receivedFinalResult = true;
          const hadDirectResponse = currentExecCount === -1;
          const hadCodeExecution = currentExecCount > 0;

          // If there is an unfinished streaming response, save it first
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

          // Clear streaming response
          setStreamingResponse('');
          setIsProcessing(false);
          wsRef.current = null;
          ws.close();
        } else if (data.type === 'result') {
          // Compatible with old result messages (if any)
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
        // If we were still processing and never received a final_result,
        // the connection was dropped unexpectedly (server restart, timeout, etc.)
        if (!receivedFinalResult) {
          // Save any accumulated streaming response as a partial result
          if (streamingResponse && streamingResponse.trim()) {
            addMessages(currentSessionId, [{
              type: 'response',
              content: streamingResponse.trim(),
              timestamp: Date.now()
            }]);
            setStreamingResponse('');
          }
          addMessages(currentSessionId, [{
            type: 'error',
            content: '⚠️ Connection lost before task completed. The backend may have restarted or the request timed out. Please try again.',
            timestamp: Date.now()
          }]);
        }
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

    // Cleanup function
    return () => {
      // Close WebSocket connection if it exists
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      // Reset parser state
      setParserState(createParserState());
    }
  }, [])

  const isLeftDragging = dragStateRef.current.isDragging === 'left';
  const isPreviewDragging = dragStateRef.current.isDragging === 'preview';

  const session = useMemo(() => {
    return getSessionById(activeSessionId)
  }, [activeSessionId, getSessionById])

  return (
    <div
      className="w-screen h-screen flex overflow-hidden"
      style={{
        paddingLeft: isLeftPanelCollapsed ? 48 : leftPanelWidth
      }}
    >
      {/* Left Panel with dynamic width */}
      <div
        className="h-screen fixed left-0 top-0 z-40"
        style={{
          width: isLeftPanelCollapsed ? 48 : leftPanelWidth,
          transition: isLeftDragging ? 'none' : 'width 0.15s ease-out'
        }}
      >
        <Suspense fallback={<LoadingPlaceholder />}>
          <LeftPanel
            sessions={sessions}
            handleChangeSession={handleChangeSession}
            handleDeleteSession={handleDeleteSession}
            isCollapsed={isLeftPanelCollapsed}
            onCollapsedChange={setIsLeftPanelCollapsed}
          />
        </Suspense>
      </div>

      {/* Left Panel Resizer */}
      {!isLeftPanelCollapsed && (
        <div
          className={`w-1.5 cursor-col-resize transition-colors ${isLeftDragging ? 'bg-blue-500' : 'bg-gray-200 hover:bg-blue-400'
            }`}
          onMouseDown={handleLeftDragStart}
          style={{
            touchAction: 'none',
            position: 'fixed',
            top: 0,
            left: (isLeftPanelCollapsed ? 48 : leftPanelWidth) - 3,
            height: '100vh',
            zIndex: 60
          }}
        />
      )}

      {/* Drag overlay to prevent losing mouse events over iframes */}
      {(isLeftDragging || isPreviewDragging) && (
        <div
          className="fixed inset-0"
          style={{
            zIndex: 55,
            cursor: 'col-resize'
          }}
        />
      )}

      <div className={`flex flex-1 flex-col h-full w-full`}>
        <div className="releative flex py-2 min-h-16 items-center justify-center bg-white border-b border-gray-200">
          <div className="w-1/2 flex justify-center items-center">
            <span className="font-semibold text-md text-gray-900 truncate">{session?.title || ''}</span>
          </div>
          <div className="absolute right-6 flex items-center gap-4">
            <User />
            <LogoutButton />
          </div>
        </div>
        {/* Main Content Area (Chat + Preview) */}
        <div ref={containerRef} className="flex flex-1 overflow-hidden w-full">
          {/* Chat Area */}
          <div
            className="flex flex-col bg-gray-50 h-full overflow-hidden shrink-0"
            style={{
              width: previewFile ? `${100 - previewWidthPercent}%` : '100%',
              transition: isPreviewDragging ? 'none' : 'width 0.15s ease-out'
            }}
          >
            <Suspense fallback={<LoadingPlaceholder />}>
              <MessageList
                messages={messages}
                currentScript={currentScript}
                onFilePreview={setPreviewFile}
                streamingResponse={streamingResponse}
                isLoading={messagesLoading}
                isCodeBlock={parserState.inCodeBlock}
              />
            </Suspense>
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
                className={`w-1.5 cursor-col-resize shrink-0 transition-colors ${isPreviewDragging ? 'bg-orange-500' : 'bg-gray-200 hover:bg-orange-400'
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
                <Suspense fallback={<LoadingPlaceholder />}>
                  <FilePreview
                    file={previewFile}
                    onClose={() => setPreviewFile(null)}
                  />
                </Suspense>
              </div>
            </>
          )}
        </div>
      </div>
      {/* {skillEditored && <SkillEditor />} */}
    </div>
  );
};

export default Chat;
