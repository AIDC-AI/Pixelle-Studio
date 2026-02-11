/**
 * Chat Storage Hook
 * Provides convenient chat history management functionality
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

  // Load messages
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

  // Save message (using optimistic update for streaming effect)
  const saveMessage = useCallback(async (sessId: string, msg: Message, messageId?: string) => {
    try {
      // Optimistic update: immediately update UI
      setMessages(prev => {
        // if type is response_delta，update last item
        if (prev?.length > 1 && prev?.[prev?.length - 2]?.type === 'response_delta' && msg?.type === 'response_delta') {
          return [...prev.slice(0, prev?.length - 2), msg];
        } else {
          return [...prev, msg];
        }
      });

      
      // Save to IndexedDB in background (non-blocking for UI)
      chatStorage.saveMessage(sessId, msg, messageId).catch(err => {
        console.error('Failed to persist message to storage:', err);
      });
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, []);

  // Batch save messages (using optimistic update for streaming effect)
  const saveMessages = useCallback(async (sessId: string, msgs: Message[]) => {
    try {
      // Optimistic update: immediately update UI
      setMessages(prev => [...prev, ...msgs]);
      
      // Save to IndexedDB in background (non-blocking for UI)
      chatStorage.saveMessages(sessId, msgs).catch(err => {
        console.error('Failed to persist messages to storage:', err);
      });
    } catch (err) {
      setError(err as Error);
      console.error('Failed to save message:', err);
      throw err;
    }
  }, []);

  // Clear current session messages
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

  // Load session list
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

  // Create new session
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

  // Delete session
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

  // Update session title
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

  // Update session backend ID
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

  // Initial load (using ref to avoid reload interrupting streaming output)
  const sessionIdRef = useRef<string | undefined>(sessionId);
  const isInitialLoadRef = useRef(true);
  
  useEffect(() => {
    // If same session, don't reload (preserve streaming output)
    if (sessionIdRef.current === sessionId && !isInitialLoadRef.current) {
      return;
    }
    
    // Only reload messages on session switch or initial load
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
    // State
    messages,
    sessions,
    sessionsLoading,
    messagesLoading,
    error,

    // Message operations
    loadMessages,
    saveMessage,
    saveMessages,
    clearMessages,

    // Session operations
    loadSessions,
    createSession,
    deleteSession,
    getSessionById,
    updateSessionTitle,
    updateSessionBackendId,
  };
}

export default useChatStorage;
