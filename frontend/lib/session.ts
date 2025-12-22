import { Message } from "@/types/message";
import { Session } from "@/types/session";

const ACTIVE_SESSION_ID_KEY = 'active_session_id'
const SESSIONS_KEY = 'sessions'

export const MAX_SESSION_COUNT = 15

export const sessionAPI = {
    // get active session id
    getActiveSessionId: (): string => {
        if (typeof window === 'undefined') {
            return ''
        }
        return localStorage.getItem(ACTIVE_SESSION_ID_KEY) || '';
    },
    // set active session id
    setActiveSessionId: (id: string): void => {
        if (typeof window === 'undefined') return;
        localStorage.setItem(ACTIVE_SESSION_ID_KEY, id);
    },

    // get sessions
    getSessions: (): Session[] => {
        if (typeof window === 'undefined') {
            return []
        }
        const ids = localStorage.getItem(SESSIONS_KEY);
        if (!!ids) {
            return JSON.parse(ids);
        }
        return []
    },
    // set sessions
    setSessions: (sessions: Session[]) => {
        if (typeof window === 'undefined') return;
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    },
    
    // get messages by sessionId
    getMessagesBySessionId: (id: string): Message[] => {
        if (typeof window === 'undefined') return [];
        const messages = localStorage.getItem(id)
        if (!!messages) {
            return JSON.parse(messages);
        }
        return []
    },
    // set messages by sessionId
    setMessagesBySessionId: (id: string, messages: Message[]): void => {
        if (typeof window === 'undefined') return;
        localStorage.setItem(id, JSON.stringify(messages));
    },
    // delete messages by sessionId
    deleteMessagesBySessionId: (id: string): void => {
        if (typeof window === 'undefined') return;
        localStorage.removeItem(id);
    }
};