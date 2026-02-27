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

/**
 * Chat Storage Hook
 * Provides convenient chat history management functionality
 * 
 * Enhanced with backend sync for cross-browser persistence:
 * - On initial load, fetches session list from backend and syncs to IndexedDB
 * - When opening a session with no local messages, fetches from backend
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { chatStorage } from '@/lib/chatStorage';
import { api } from '@/lib/api';
import { Message } from '@/types/message';
import { Session } from '@/types/session';

export function useChatStorage(sessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Track the current active session ID in a ref for use in callbacks
  const currentSessionIdRef = useRef<string | undefined>(sessionId);
  useEffect(() => {
    currentSessionIdRef.current = sessionId;
  }, [sessionId]);

  // Load messages - first try IndexedDB, then fallback to backend
  const loadMessages = useCallback(async (sessId: string) => {
    if (!sessId) return;
    
    setMessagesLoading(true);
    setError(null);
    try {
      // First try local IndexedDB
      const localMsgs = await chatStorage.getMessages(sessId);
      if (localMsgs.length > 0) {
        setMessages(localMsgs);
        setMessagesLoading(false);
        return;
      }
      
      // No local messages - find the backend session ID
      const session = await chatStorage.getSession(sessId);
      if (session?.backendSessionId) {
        try {
          const backendData = await api.getSessionMessages(session.backendSessionId);
          if (backendData.messages && backendData.messages.length > 0) {
            // Save to local IndexedDB for future access
            await chatStorage.importMessagesFromBackend(sessId, backendData.messages);
            setMessages(backendData.messages);
          } else {
            setMessages([]);
          }
        } catch (err) {
          console.warn('Failed to load messages from backend, using empty:', err);
          setMessages([]);
        }
      } else {
        setMessages([]);
      }
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
      // Optimistic update: only update UI if this message belongs to the currently viewed session
      if (sessId === currentSessionIdRef.current) {
        setMessages(prev => {
          // if type is response_delta，update last item
          if (prev?.length > 1 && prev?.[prev?.length - 2]?.type === 'response_delta' && msg?.type === 'response_delta') {
            return [...prev.slice(0, prev?.length - 2), msg];
          } else {
            return [...prev, msg];
          }
        });
      }

      
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
      // Optimistic update: only update UI if these messages belong to the currently viewed session
      if (sessId === currentSessionIdRef.current) {
        setMessages(prev => [...prev, ...msgs]);
      }
      
      // Always save to IndexedDB regardless of current view (non-blocking for UI)
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

  // Load session list - sync from backend then merge with local
  const loadSessions = useCallback(async (uid?: number) => {
    setSessionsLoading(true);
    setError(null);
    try {
      // First load local sessions
      let localSessions = await chatStorage.getSessions();
      
      // If user is logged in, sync from backend
      if (uid) {
        try {
          const backendSessions = await api.getUserSessions(uid);
          if (backendSessions && backendSessions.length > 0) {
            // Merge backend sessions into local IndexedDB
            localSessions = await chatStorage.syncSessionsFromBackend(backendSessions);
          }
        } catch (err) {
          console.warn('Failed to sync sessions from backend, using local only:', err);
        }
      }
      
      setSessions(localSessions);
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

  // Delete session (both local and backend)
  const deleteSession = useCallback(async (sessId: string) => {
    try {
      // Find backend session ID before deleting locally
      const session = await chatStorage.getSession(sessId);
      const backendSessionId = session?.backendSessionId;
      
      // Delete from local IndexedDB
      await chatStorage.deleteSession(sessId);
      setSessions((prev) => prev.filter((s) => s.id !== sessId));
      
      // Also delete from backend (fire and forget)
      if (backendSessionId) {
        api.deleteUserSession(backendSessionId).catch(err => {
          console.warn('Failed to delete session from backend:', err);
        });
      }
    } catch (err) {
      setError(err as Error);
      console.error('Failed to delete session:', err);
      throw err;
    }
  }, []);


  const getSessionById = useCallback((id: string) => {
    return sessions.find((s) => s.id === id) || null
  }, [sessions]);

  // Update session title (both local and backend)
  const updateSessionTitle = useCallback(async (sessId: string, title: string) => {
    try {
      await chatStorage.updateSessionTitle(sessId, title);
      setSessions((prev) =>
        prev.map((s) => (s.id === sessId ? { ...s, title } : s))
      );
      
      // Also save to backend (fire and forget)
      const session = await chatStorage.getSession(sessId);
      if (session?.backendSessionId) {
        api.updateSessionTitle(session.backendSessionId, title).catch(err => {
          console.warn('Failed to save title to backend:', err);
        });
      }
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
