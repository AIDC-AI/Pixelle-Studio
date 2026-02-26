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

const ACTIVE_SESSION_ID_PREFIX = 'active_session_id'

/**
 * Get the storage key for the active session ID, scoped by user.
 */
function getKey(uid?: number): string {
    if (uid) {
        return `${ACTIVE_SESSION_ID_PREFIX}_${uid}`;
    }
    return ACTIVE_SESSION_ID_PREFIX;
}

export const sessionAPI = {
    // get active session id (user-scoped)
    getActiveSessionId: (uid?: number): string => {
        if (typeof window === 'undefined') {
            return ''
        }
        return localStorage.getItem(getKey(uid)) || '';
    },
    // set active session id (user-scoped)
    setActiveSessionId: (id: string, uid?: number): void => {
        if (typeof window === 'undefined') return;
        localStorage.setItem(getKey(uid), id);
    },
    // clear active session id on logout
    clearActiveSessionId: (uid?: number): void => {
        if (typeof window === 'undefined') return;
        localStorage.removeItem(getKey(uid));
        // Also clear the legacy key (without uid)
        localStorage.removeItem(ACTIVE_SESSION_ID_PREFIX);
    }
};
