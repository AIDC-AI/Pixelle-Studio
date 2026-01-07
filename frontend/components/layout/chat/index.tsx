'use client'

import { Message, ExecutionResult, OutputFile } from "@/types/message";
import { useEffect, useState } from "react";
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

    const handleSubmit = async () => {
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
          // NEW: Handle code generation event
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
          // NEW: Handle execution result event
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
          // NEW: Handle direct response from agent
          _messages.push({
            type: 'response',
            content: data.content,
            timestamp: Date.now()
          })
          // Mark that we received a direct response
          // So we don't show duplicate content in final_result
          currentExecCount = -1; // Use -1 as a flag for direct response
        } else if (data.type === 'skill_loaded') {
          // NEW: Handle skill loaded event
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
              _messages.push({
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
        <LeftPanel 
          sessions={sessions} 
          handleDeleteSession={handleDeleteSession}
        />
        <div className="flex flex-col bg-linear-to-br from-slate-50 to-slate-100 w-full h-full overflow-x-hidden">
            <MessageList 
                messages={messages} 
                currentScript={currentScript} 
            />
            <Input 
              isProcessing={isProcessing}
              input={input}
              setInput={setInput}
              fileList={fileList}
              setFileList={setFileList}
              handleSubmit={handleSubmit}
            />
        </div>
        {
          skillEditored && <SkillEditor />
        }
        
      </div>
    );
};

export default Chat;
