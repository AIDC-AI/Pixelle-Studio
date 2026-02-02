/**
 * 聊天存储 Hook
 * 提供便捷的聊天记录管理功能
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { chatStorage } from '@/lib/chatStorage';
import { Message } from '@/types/message';
import { Session } from '@/types/session';

export function useChatStorage(sessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 加载消息
  const loadMessages = useCallback(async (sessId: string) => {
    if (!sessId) return;
    
    setMessagesLoading(true);
    setError(null);
    try {
      const msgs = await chatStorage.getMessages(sessId);
      setMessages(msgs);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to load messages:', err);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  // 保存消息（使用乐观更新实现流式效果）
  const saveMessage = useCallback(async (sessId: string, msg: Message, messageId?: string) => {
    try {
      // 乐观更新：立即更新 UI
      setMessages(prev => [...prev, msg]);
      
      // 后台保存到 IndexedDB（不阻塞 UI）
      chatStorage.saveMessage(sessId, msg, messageId).catch(err => {
        console.error('Failed to persist message to storage:', err);
      });
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, []);

  // 批量保存消息（使用乐观更新实现流式效果）
  const saveMessages = useCallback(async (sessId: string, msgs: Message[]) => {
    try {
      // 乐观更新：立即更新 UI
      setMessages(prev => [...prev, ...msgs]);
      
      // 后台保存到 IndexedDB（不阻塞 UI）
      chatStorage.saveMessages(sessId, msgs).catch(err => {
        console.error('Failed to persist messages to storage:', err);
      });
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, []);

  // 清空当前会话消息
  const clearMessages = useCallback(async (sessId: string) => {
    try {
      await chatStorage.deleteMessages(sessId);
      setMessages([]);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to clear messages:', err);
      throw err;
    }
  }, []);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    setError(null);
    try {
      const sess = await chatStorage.getSessions();
      setSessions(sess);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  // 创建新会话
  const createSession = useCallback(async (title?: string, backendSessionId?: string) => {
    try {
      const session = await chatStorage.createSession(title, backendSessionId);
      setSessions((prev) => [session, ...prev]);
      return session;
    } catch (err) {
      setError(err as Error);
      console.error('Failed to create session:', err);
      throw err;
    }
  }, []);

  // 删除会话
  const deleteSession = useCallback(async (sessId: string) => {
    try {
      await chatStorage.deleteSession(sessId);
      setSessions((prev) => prev.filter((s) => s.id !== sessId));
    } catch (err) {
      setError(err as Error);
      console.error('Failed to delete session:', err);
      throw err;
    }
  }, []);


  const getSessionById = useCallback((id: string) => {
    return sessions.find((s) => s.id === id) || null
  }, [sessions]);

  // 更新会话标题
  const updateSessionTitle = useCallback(async (sessId: string, title: string) => {
    try {
      await chatStorage.updateSessionTitle(sessId, title);
      setSessions((prev) =>
        prev.map((s) => (s.id === sessId ? { ...s, title } : s))
      );
    } catch (err) {
      setError(err as Error);
      console.error('Failed to update session title:', err);
      throw err;
    }
  }, []);

  // 更新会话的后端 ID
  const updateSessionBackendId = useCallback(async (sessId: string, backendSessionId: string) => {
    try {
      await chatStorage.updateSessionBackendId(sessId, backendSessionId);
      setSessions((prev) =>
        prev.map((s) => (s.id === sessId ? { ...s, backendSessionId } : s))
      );
    } catch (err) {
      setError(err as Error);
      console.error('Failed to update session backend ID:', err);
      throw err;
    }
  }, []);

  // 初始加载（使用 ref 避免重新加载导致流式输出中断）
  const sessionIdRef = useRef<string | undefined>(sessionId);
  const isInitialLoadRef = useRef(true);
  
  useEffect(() => {
    // 如果是同一个session，不重新加载（保持流式输出）
    if (sessionIdRef.current === sessionId && !isInitialLoadRef.current) {
      return;
    }
    
    // Session切换或初始加载时才重新加载消息
    sessionIdRef.current = sessionId;
    isInitialLoadRef.current = false;
    
    if (!!sessionId && sessionId !== '') {
      loadMessages(sessionId);
    } else {
      setMessages([])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps  
  }, [sessionId]);

  return {
    // 状态
    messages,
    sessions,
    sessionsLoading,
    messagesLoading,
    error,

    // 消息操作
    loadMessages,
    saveMessage,
    saveMessages,
    clearMessages,

    // 会话操作
    loadSessions,
    createSession,
    deleteSession,
    getSessionById,
    updateSessionTitle,
    updateSessionBackendId,
  };
}

export default useChatStorage;
