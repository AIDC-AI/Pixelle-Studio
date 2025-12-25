'use client'

import React, { createContext, useContext, useEffect, useState } from 'react';
import { sessionAPI } from '@/lib/sessionApi';
import { message } from 'antd';
import { MessageInstance } from 'antd/es/message/interface';
import { UserResponse } from '@/types/user';
import { userAPI } from '@/lib/userApi';
import { useRouter, usePathname } from 'next/navigation';

type IProps = {
    user: UserResponse | null
    setUser: React.Dispatch<React.SetStateAction<UserResponse | null>>

    token: string | null
    setToken: React.Dispatch<React.SetStateAction<string | null>>

    activeSessionId: string
    setActiveSessionId: React.Dispatch<React.SetStateAction<string>>

    messageApi: MessageInstance

    login: (email: string, password: string) => Promise<void>
    register: (username: string, email: string, password: string) => Promise<boolean>
    logout: () => void
};

const AppContext = createContext<IProps | null>(null);

const PUBLIC_ROUTES = ['/auth']

export function AppProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [user, setUser] = useState<UserResponse | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [activeSessionId, setActiveSessionId] = useState<string>('');
    const [messageApi, contextHolder] = message.useMessage();

    const login = async (email: string, password: string) => {
        try {
            const res = await userAPI.login(email, password)
            if (!!res) {
                userAPI.setToken(res.token.access_token)
                setToken(res.token.access_token)
                setUser(res.user)
            }
        } catch (error) {
            messageApi.error((error as Error)?.message || 'Login Failed!')
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
                messageApi.success('Register Successed!')
                return true
            }
        } catch (error) {
            messageApi.error((error as Error)?.message || 'Register Failed!')
        }
        return false
    } 

    const logout = () => {
        try {
            setUser(null)
            setToken(null)
            userAPI.logout()
            messageApi.success('Logout Successed!')
        } catch (error) {
            messageApi.error((error as Error)?.message || 'Logout Failed!')
        }
    }

    const getCurrentUser = async () => {
        const user = await userAPI.getCurrentUser()
        if (!!user) {
            setUser(user)
            setToken(userAPI.getToken())
        } else {
            userAPI.clearToken()
            setUser(null)
            setToken(null)
        }
    }

    useEffect(() => {
        setActiveSessionId(sessionAPI.getActiveSessionId())
    }, [])
    
    useEffect(() => {
        const isAuthRoute = PUBLIC_ROUTES.includes(pathname);
        if (!!userAPI.isAuthenticated() && !!isAuthRoute) {
            getCurrentUser()

        } else {

        }
    }, [token, router, pathname])

    return <AppContext.Provider
        value={
            {
                user, 
                setUser,
                token, 
                setToken,
                activeSessionId, 
                setActiveSessionId, 
                messageApi,
                login,
                register,
                logout
            }
        }
    >
        {contextHolder}
        {children}
    </AppContext.Provider>;
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}