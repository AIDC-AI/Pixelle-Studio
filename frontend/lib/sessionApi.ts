const ACTIVE_SESSION_ID_KEY = 'active_session_id'

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
    }
};