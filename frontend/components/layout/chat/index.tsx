// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client'

import { Message, ExecutionResult, OutputFile } from "@/types/message";
import { useEffect, useState, useRef, useCallback, lazy, Suspense, useMemo } from "react";
import { api } from "@/lib/api";
import { API_BASE } from "@/lib/data";
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
import SettingsModal from "@/components/ui/settingsModal";
import { WelcomePrompt } from "./welcomePrompts";
import { userAPI } from "@/lib/userApi";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";

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
    justLoggedIn,
    setJustLoggedIn,
  } = useApp();

  const router = useRouter();

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

  // Settings modal state
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [isFirstTimeSetup, setIsFirstTimeSetup] = useState<boolean>(false);

  // LLM settings state
  const [hasApiKeyConfigured, setHasApiKeyConfigured] = useState<boolean>(false);
  const [llmSettingsChecked, setLlmSettingsChecked] = useState<boolean>(false);

  // WebSocket reference, used to stop inference
  const wsRef = useRef<WebSocket | null>(null);

  // Track which session the current WebSocket belongs to
  const wsSessionIdRef = useRef<string | null>(null);
  // Track the active session ID in a ref for use in WebSocket callbacks
  const activeSessionIdRef = useRef<string>(activeSessionId);

  // Keep activeSessionIdRef in sync with activeSessionId
  // Also clear streaming state when switching away from the WS session
  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
    // If the user switched to a session that is NOT the one with the active WebSocket,
    // clear the streaming display to prevent content leaking
    if (wsSessionIdRef.current && wsSessionIdRef.current !== activeSessionId) {
      setStreamingResponse('');
      setCurrentScript(null);
      setParserState(createParserState());
    }
  }, [activeSessionId]);

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
    // Clear streaming state when switching sessions to prevent content leaking
    setStreamingResponse('');
    setCurrentScript(null);
    setParserState(createParserState());
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
    sessionAPI.setActiveSessionId(id, user?.uid)
  }

  // Stop inference
  const handleStop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    wsSessionIdRef.current = null;
    setIsProcessing(false);
    // Reset parser state
    setParserState(createParserState());
  }, []);

  // Check LLM settings
  const checkLLMSettings = useCallback(async () => {
    if (!user?.uid) return;
    try {
      const settings = await userAPI.getLLMSettings();
      setHasApiKeyConfigured(settings.api_key_set);
      setLlmSettingsChecked(true);
      return settings.api_key_set;
    } catch (err) {
      console.error('Failed to check LLM settings:', err);
      setLlmSettingsChecked(true);
      return false;
    }
  }, [user?.uid]);

  // Post-login settings check: if just logged in and no API key, prompt settings
  useEffect(() => {
    if (user?.uid && justLoggedIn) {
      setJustLoggedIn(false);
      checkLLMSettings().then((hasKey) => {
        if (!hasKey) {
          setIsFirstTimeSetup(true);
          setSettingsOpen(true);
        }
      });
    } else if (user?.uid && !llmSettingsChecked) {
      // Also check settings on initial load (existing session)
      checkLLMSettings();
    }
    if (!user) {
      setLlmSettingsChecked(false);
      setHasApiKeyConfigured(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.uid, justLoggedIn]);

  // Handle prompt click from welcome prompts
  const handlePromptClick = useCallback(async (prompt: WelcomePrompt) => {
    if (!user) {
      // Not logged in, redirect to auth
      router.push('/auth');
      return;
    }
    if (!hasApiKeyConfigured) {
      // Logged in but no API key, open settings
      setIsFirstTimeSetup(true);
      setSettingsOpen(true);
      return;
    }

    // Logged in and configured: set input and auto-submit with file if needed
    let promptFiles: UploadFile[] = [];
    if (prompt.hasFile && prompt.fileUrl && prompt.fileName) {
      try {
        // Fetch the file from public assets
        const response = await fetch(prompt.fileUrl);
        const blob = await response.blob();
        const file = new File([blob], prompt.fileName, { type: blob.type });

        // Upload to backend
        const formData = new FormData();
        formData.append('file', file);
        const uploadRes = await fetch(`${API_BASE}/upload${user?.uid ? `?user_id=${user.uid}` : ''}`, {
          method: 'POST',
          body: formData,
        });
        const uploadData = await uploadRes.json();

        promptFiles = [{
          uid: `prompt-${Date.now()}`,
          name: prompt.fileName,
          status: 'done' as const,
          url: uploadData.url,
          size: blob.size,
          response: uploadData,
        }];
      } catch (err) {
        console.error('Failed to upload example file:', err);
      }
    }

    // Submit directly with override parameters
    handleSubmit(prompt.prompt, promptFiles);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, hasApiKeyConfigured, router]);

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

  const handleSubmit = async (overrideInput?: string, overrideFiles?: UploadFile[]) => {
    const effectiveInput = overrideInput ?? input;
    const effectiveFileList = overrideFiles ?? fileList;

    console.log('[DEBUG] handleSubmit called, input:', effectiveInput, 'isProcessing:', isProcessing, 'user:', user);
    if (!effectiveInput.trim() || isProcessing || !user?.uid) {
      console.log('[DEBUG] handleSubmit blocked: input empty?', !effectiveInput.trim(), 'isProcessing?', isProcessing, 'no user.uid?', !user?.uid);
      return;
    }

    // Check if any files are still uploading
    const uploadingFiles = effectiveFileList.filter(f => f.status === 'uploading');
    if (uploadingFiles.length > 0) {
      console.log('[DEBUG] Waiting for file upload to complete...');
      return; // Block submission, wait for upload to complete
    }

    // Only select files that have finished uploading (status === 'done')
    const doneFiles = effectiveFileList.filter(f => f.status === 'done');

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
      session = await handleNewSession(effectiveInput)

      // Async title generation (non-blocking)
      api.generateTitle(effectiveInput, user?.uid).then(({ title }) => {
        if (title) {
          // Backend already constrains title to 50 chars; just use it directly
          updateSessionTitle(session!.id, title.trim());
        }
      }).catch((err) => {
        console.error('Failed to generate title:', err);
        // Use first 20 characters of input as fallback
        const fallbackTitle = effectiveInput.length > 20 ? effectiveInput.substring(0, 20) + '...' : effectiveInput;
        updateSessionTitle(session!.id, fallbackTitle);
      });
    }
    const currentSessionId = session.id;
    const backendSessionId = session.backendSessionId;

    // Save current message
    addMessages(currentSessionId, [{
      type: 'user',
      content: effectiveInput,
      outputFiles,
      timestamp: Date.now()
    }])

    let currentExecCount = 0;
    let receivedFinalResult = false;

    try {
      // 1. Create Chat (backend will auto-select tools)
      const { chat_id, session_id } = await api.createChat(
        effectiveInput,
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
      wsSessionIdRef.current = currentSessionId;

      // Helper: only update streaming UI state if the user is still viewing this session
      const isActiveSession = () => activeSessionIdRef.current === currentSessionId;

      // Immediately show "task in progress" status hint (using streamingResponse)
      if (isActiveSession()) {
        setStreamingResponse('Task in progress, waiting for response...');
      }

      let lastType = ''
      let streamingString = ''
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Ignore heartbeat messages (keepalive from backend)
        if (data.type === 'heartbeat') return;

        const _messages: Message[] = []

        if (lastType === 'response_delta' && data.type !== 'response_delta' && !!streamingString && streamingString.trim() !== '') {
          // if type is not final_result, add delta to messages
          if (data.type !== 'final_result') {
            _messages.push({
              type: 'response',
              content: streamingString.trim(),
              timestamp: Date.now()
            })
          }
          lastType = ''
          streamingString = ''
          if (isActiveSession()) {
            setStreamingResponse('');
          }
        }

        if (data.type === 'response_delta') {
          lastType = 'response_delta'
          const deltaContent = data.accumulated || '';
          // Filter code blocks from the content
          const { filtered, state: newParserState } = filterCodeBlocks(deltaContent.trim(), parserState);
          if (isActiveSession()) {
            setParserState(newParserState);
            // Update state - show filtered reasoning text
            setStreamingResponse(filtered);
          }
          streamingString = filtered;
        } else if (data.type === 'iteration_start') {
          // Clear "task in progress..." hint
          // setStreamingResponse('');
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
          if (isActiveSession()) setCurrentScript(data.content);
          _messages.push({
            type: 'system',
            content: `📝 Generated script (iteration ${data.iteration})`,
            timestamp: Date.now(),
            iteration: data.iteration
          })
        } else if (data.type === 'code') {
          // === Before showing code, save accumulated reasoning text ===
          // if (streamingResponse && streamingResponse.trim()) {
          //   _messages.push({
          //     type: 'response',
          //     content: streamingResponse.trim(),
          //     timestamp: Date.now()
          //   });
          // }
          // setStreamingResponse('');
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
          // Derive the base URL from API_BASE (strip trailing /api)
          const filesBaseUrl = API_BASE.replace(/\/api\/?$/, '');
          let fileUrl = '';
          const scriptsMatch = filePath.match(/scripts\/(.+)$/);
          if (scriptsMatch) {
            fileUrl = `${filesBaseUrl}/files/${scriptsMatch[1]}`;
          } else {
            // If path format doesn't match, try using relative_path directly
            fileUrl = `${filesBaseUrl}/files/${relativePath}`;
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

          // Auto-preview previewable files (only if viewing this session)
          if (isActiveSession()) autoPreviewFile([outputFile]);
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

            // Auto-preview previewable files (only if viewing this session)
            if (isActiveSession()) autoPreviewFile(outputFiles);
          }

          // After code execution completes, reset tool call flag to allow subsequent streaming output
          hasToolCallsRef.current = false;
          // Reset parser state, prepare to receive new reasoning text
          if (isActiveSession()) setParserState(createParserState());
        } else if (data.type === 'response') {
          // Handle direct response from agent (complete response, non-streaming)
          // If there is accumulated streaming content, use it; otherwise use data.content
          // const finalContent = streamingResponse || data.content;
          const finalContent = data.content;
          if (finalContent) {
            _messages.push({
              type: 'response',
              content: finalContent,
              timestamp: Date.now()
            })
          }
          // Clear streaming response
          // setStreamingResponse('');
          // Mark that we received a direct response
          // So we don't show duplicate content in final_result
          currentExecCount = -1; // Use -1 as a flag for direct response
        } else if (data.type === 'tool_call') {
          // Mark tool call, stop streaming output
          hasToolCallsRef.current = true;
          
          // === Critical fix: save accumulated reasoning text before clearing streaming response ===
          // if (streamingResponse && streamingResponse.trim()) {
          //   _messages.push({
          //     type: 'response',
          //     content: streamingResponse.trim(),
          //     timestamp: Date.now()
          //   });
          // }
          // // Clear streaming response
          // setStreamingResponse('');

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
          // setStreamingResponse('');
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
          if (streamingString && streamingString.trim()) {
            _messages.push({
              type: 'response',
              content: streamingString.trim(),
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

          // Clear streaming response only if user is still viewing this session
          if (isActiveSession()) {
            setStreamingResponse('');
          }
          setIsProcessing(false);
          wsRef.current = null;
          wsSessionIdRef.current = null;
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
          wsSessionIdRef.current = null;
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
        wsSessionIdRef.current = null;
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        // If we were still processing and never received a final_result,
        // the connection was dropped unexpectedly (server restart, timeout, etc.)
        if (!receivedFinalResult) {
          // Save any accumulated streaming response as a partial result
          if (streamingString && streamingString.trim()) {
            addMessages(currentSessionId, [{
              type: 'response',
              content: streamingString.trim(),
              timestamp: Date.now()
            }]);
            if (isActiveSession()) {
              setStreamingResponse('');
            }
          }
          addMessages(currentSessionId, [{
            type: 'error',
            content: '⚠️ Connection lost before task completed. The backend may have restarted or the request timed out. Please try again.',
            timestamp: Date.now()
          }]);
        }
        setIsProcessing(false);
        wsRef.current = null;
        wsSessionIdRef.current = null;
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
        // Pass uid so sessions can be synced from backend
        await loadSessions(user?.uid)
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.uid])

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
        className="fixed left-0 top-0 z-40"
        style={{
          width: isLeftPanelCollapsed ? 48 : leftPanelWidth,
          height: '100vh',
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
            {user ? (
              <>
                <button
                  onClick={() => setSettingsOpen(true)}
                  className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
                  title="LLM Settings"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
                <User />
                <LogoutButton />
              </>
            ) : (
              <button
                onClick={() => router.push('/auth')}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                <LogIn className="w-4 h-4" />
                <span>Login</span>
              </button>
            )}
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
                onOpenSettings={() => setSettingsOpen(true)}
                onPromptClick={handlePromptClick}
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
      
      {/* Settings Modal */}
      <SettingsModal
        open={settingsOpen}
        isFirstTimeSetup={isFirstTimeSetup}
        onClose={() => {
          setSettingsOpen(false);
          setIsFirstTimeSetup(false);
          // Refetch LLM settings after modal closes (in case user saved)
          if (user?.uid) {
            checkLLMSettings();
          }
        }}
      />
    </div>
  );
};

export default Chat;
