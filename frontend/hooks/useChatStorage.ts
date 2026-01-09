/**
 * 聊天存储 Hook
 * 提供便捷的聊天记录管理功能
 */

import { useState, useEffect, useCallback } from 'react';
import { chatStorage } from '@/lib/chatStorage';
import { Message } from '@/types/message';
import { Session } from '@/types/session';

export function useChatStorage(sessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 加载消息
  const loadMessages = useCallback(async (sessId: string) => {
    if (!sessId) return;
    
    setLoading(true);
    setError(null);
    try {
      const msgs = await chatStorage.getMessages(sessId);
      setMessages(msgs);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to load messages:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // 保存消息
  const saveMessage = useCallback(async (sessId: string, msg: Message, messageId?: string) => {
    try {
      await chatStorage.saveMessage(sessId, msg, messageId);
      // 重新加载消息以保持同步
      await loadMessages(sessId)
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, [loadMessages]);

  // 批量保存消息
  const saveMessages = useCallback(async (sessId: string, msgs: Message[]) => {
    try {
      await chatStorage.saveMessages(sessId, msgs);
      // 重新加载消息以保持同步
      await loadMessages(sessId)
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, [loadMessages]);

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
    setLoading(true);
    setError(null);
    try {
      const sess = await chatStorage.getSessions();
      setSessions(sess);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
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

  // 初始加载
  useEffect(() => {
    if (!!sessionId && sessionId !== '') {
      loadMessages(sessionId);
    } else {
      setMessages([])
    }
  }, [sessionId, loadMessages]);

  return {
    // 状态
    messages,
    sessions,
    loading,
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
    updateSessionTitle,
    updateSessionBackendId,
  };
}

export default useChatStorage;
