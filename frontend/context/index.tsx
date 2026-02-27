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

import { createContext, Dispatch, SetStateAction, useContext, useEffect, useRef, useState } from 'react';
import { sessionAPI } from '@/lib/sessionApi';
import { UserResponse } from '@/types/user';
import { userAPI } from '@/lib/userApi';
import { chatStorage } from '@/lib/chatStorage';
import { useRouter, usePathname } from 'next/navigation';

import { Toast } from 'radix-ui';
import { Check, Lightbulb, X } from 'lucide-react';

export enum ToastType {
    SUCCESS = 'success',
    ERROR = 'error',
    INFO = 'info'
}

type IProps = {
    user: UserResponse | null
    setUser: Dispatch<SetStateAction<UserResponse | null>>

    token: string | null
    setToken: Dispatch<SetStateAction<string | null>>

    activeSessionId: string
    setActiveSessionId: Dispatch<SetStateAction<string>>

    justLoggedIn: boolean
    setJustLoggedIn: Dispatch<SetStateAction<boolean>>

    login: (email: string, password: string) => Promise<void>
    register: (username: string, email: string, password: string) => Promise<boolean>
    logout: () => Promise<void>

    showToast: (type: ToastType, text: string) => void
    hideToast: () => void
};

const AppContext = createContext<IProps | null>(null);

const PUBLIC_ROUTES = ['/auth']

export function AppProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();

    const [user, setUser] = useState<UserResponse | null>(null)
    const [token, setToken] = useState<string | null>(null)

    const [activeSessionId, setActiveSessionId] = useState<string>('');
    const [justLoggedIn, setJustLoggedIn] = useState<boolean>(false);

    const [toastOpen, setToastOpen] = useState<boolean>(false)
    const [toastType, setToastType] = useState<ToastType>(ToastType.INFO)
    const [toastContent, setToastContent] = useState<string>('')
    const timerRef = useRef<number | null>(null);

    const login = async (email: string, password: string) => {
        try {
            const res = await userAPI.login(email, password)
            if (!!res) {
                userAPI.setToken(res.token.access_token)
                setToken(res.token.access_token)
                setUser(res.user)
                setJustLoggedIn(true)
                // Switch IndexedDB to user-scoped database
                await chatStorage.switchUser(res.user.uid)
                // Load user-scoped active session ID
                const savedSessionId = sessionAPI.getActiveSessionId(res.user.uid)
                setActiveSessionId(savedSessionId || '')
            }
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "Login failed!")
        }
    }

    const register = async (username: string, email: string, password: string) => {
        try {
            const res = await userAPI.createUser({
                username,
                email,
                password
            })
            if (!!res) {
                showToast(ToastType.SUCCESS, "Registration successful!")
                return true
            }
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "Registration failed!")
        }
        return false
    } 

    const logout = async () => {
        try {
            // Clear active session for current user before clearing user state
            sessionAPI.clearActiveSessionId(user?.uid)
            setUser(null)
            setToken(null)
            setActiveSessionId('')
            userAPI.logout()
            // Close user-scoped IndexedDB on logout
            await chatStorage.onLogout()
            showToast(ToastType.SUCCESS, "Logged out successfully!")
        } catch (error) {
            showToast(ToastType.ERROR, (error as Error)?.message || "Logout failed!")
        }
    }

    const showToast = (type: ToastType, text: string) => {
        setToastOpen(true)
        setToastType(type)
        setToastContent(text)
        clearTimeout()
        timerRef.current = window.setTimeout(hideToast, 2000)
    }

    const hideToast = () => {
        setToastOpen(false)
        setToastType(ToastType.INFO)
        setToastContent('')
    }

    const getCurrentUser = async () => {
        try {
            const fetchedUser = await userAPI.getCurrentUser()
            if (!!fetchedUser) {
                setUser(fetchedUser)
                setToken(userAPI.getToken())
                // Switch IndexedDB to user-scoped database
                await chatStorage.switchUser(fetchedUser.uid)
                // Load user-scoped active session ID
                const savedSessionId = sessionAPI.getActiveSessionId(fetchedUser.uid)
                if (savedSessionId) {
                    setActiveSessionId(savedSessionId)
                }
            } else {
                userAPI.clearToken()
                setUser(null)
                setToken(null)
                await chatStorage.onLogout()
            }
        } catch {
            userAPI.clearToken()
            setUser(null)
            setToken(null)
            await chatStorage.onLogout()
        }
    }

    const clearTimeout = () => {
        if (timerRef.current) {
            window.clearTimeout(timerRef.current)
            timerRef.current = null
        }
    }

    const renderToastContent = () => {
        let icon
        let iconColor = ''
        switch (toastType) {
            case ToastType.SUCCESS:
                icon = <Check />
                iconColor = "bg-success"
            break;
            case ToastType.ERROR:
                icon = <X />
                iconColor = "bg-error"
            break;
            case ToastType.INFO:
            default:
                icon = <Lightbulb />
                iconColor = "bg-info"
            break;
        }
        return <div className='flex flex-row gap-2 items-center'>
            <div className={`w-4 h-4 text-white p-0.75 rounded-full flex justify-center items-center ${iconColor}`}>
                {icon}
            </div>
            {toastContent}
        </div>
    }

    useEffect(() => {
        // Initialize: if token exists, fetch user info
        // Active session ID will be loaded after user is authenticated (user-scoped)
        const initAuth = async () => {
            if (userAPI.isAuthenticated() && !user) {
                await getCurrentUser()
            }
        }
        initAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
    
    useEffect(() => {
        const isAuthRoute = PUBLIC_ROUTES.includes(pathname);
        const isHomePage = pathname === '/';
        
        if (userAPI.isAuthenticated() && user) {
            // Logged in with user info: if on auth page, redirect to home
            if (isAuthRoute) {
                router.push('/')
            }
        } else if (!userAPI.isAuthenticated()) {
            // Not logged in: allow home page (to show welcome prompts)
            // Only redirect from other protected routes
            if (!isAuthRoute && !isHomePage) {
                router.push('/auth')
            }
        }
        // If isAuthenticated but user is null (still loading), don't redirect
    }, [pathname, user])

    return <AppContext.Provider
        value={
            {
                user, 
                setUser,
                token, 
                setToken,
                activeSessionId, 
                setActiveSessionId, 
                justLoggedIn,
                setJustLoggedIn,
                login,
                register,
                logout,
                showToast,
                hideToast
            }
        }
    >
        {children}
        <Toast.Provider swipeDirection="up">
			<Toast.Root 
                className="bg-white text-sm text-gray-900 rounded-md px-4 py-2 flex justify-center items-center
                shadow-[0_10px_38px_-10px_hsl(206_22%_7%/35%),0_10px_20px_-15px_hsl(206_22%_7%/20%)]
                data-[state=open]:animate-slideIn data-[state=closed]:animate-hide" 
                open={toastOpen} 
                onOpenChange={setToastOpen}
            >
				{/* <Toast.Title className="ToastTitle">{toastDetail?.title}</Toast.Title> */}
				<Toast.Description asChild>
					{renderToastContent()}
				</Toast.Description>
			</Toast.Root>
			<Toast.Viewport className="fixed top-4 left-1/2 -translate-x-1/2 flex flex-col z-9999 outline-none" />
		</Toast.Provider>
    </AppContext.Provider>;
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}