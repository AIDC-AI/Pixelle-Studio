'use client'

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { mcpServerAPI, type MCPServerConfig } from '../lib/mcpConfig';
import { sessionAPI } from '@/lib/session';
import { Session } from '@/types/session';
import { Message } from '@/types/message';
import { message } from 'antd';
import { MessageInstance } from 'antd/es/message/interface';

type MessageMap = Record<string, Message[] | null> 

type IProps = {
    config: MCPServerConfig
    setConfig: React.Dispatch<React.SetStateAction<MCPServerConfig>>

    activeSessionId: string
    setActiveSessionId: React.Dispatch<React.SetStateAction<string>>

    sessions: Session[]
    setSessions: React.Dispatch<React.SetStateAction<Session[]>>

    sessionMessages: MessageMap
    setSessionMessages: React.Dispatch<React.SetStateAction<MessageMap>>

    messageApi: MessageInstance

    deleteSession: (id: string) => void 
};

const AppContext = createContext<IProps | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
    const [config, setConfig] = useState<MCPServerConfig>(mcpServerAPI.loadConfig());
    const [activeSessionId, setActiveSessionId] = useState<string>('');
    const [sessions, setSessions] = useState<Session[]>([])
    const [sessionMessages, setSessionMessages] = useState<MessageMap>({});
    const [messageApi, contextHolder] = message.useMessage();
    
    const isInit = useRef<boolean>(true)
    
    const deleteSession = (id: string) => {
        setSessions(prev => [...prev.filter((session) => session.id !== id)])
        if (activeSessionId === id) {
            setActiveSessionId('')
        }
        setSessionMessages(prev => ({
            ...prev,
            [id]: null
        }))
        sessionAPI.deleteMessagesBySessionId(id)
    }

    useEffect(() => {
        if (isInit.current)
            return
        sessionAPI.setActiveSessionId(activeSessionId)
        if (!!activeSessionId && activeSessionId !== '' && !sessionMessages[activeSessionId]) {
            const messages = sessionAPI.getMessagesBySessionId(activeSessionId)
            if (messages?.length > 0) {
                setSessionMessages({
                    ...sessionMessages,
                    [activeSessionId]: messages
                })
            }
        }
    }, [activeSessionId])

    useEffect(() => {
        if (isInit.current)
            return
        sessionAPI.setSessions(sessions)
    }, [sessions])

    useEffect(() => {
        if (isInit.current) {
            setActiveSessionId(sessionAPI.getActiveSessionId())
            setSessions(sessionAPI.getSessions())
            isInit.current = false
        }
    }, [])
    
    return <AppContext.Provider
        value={
            {
                config,
                setConfig,
                activeSessionId, 
                setActiveSessionId, 
                sessions, 
                setSessions,
                sessionMessages, 
                setSessionMessages,
                messageApi,
                deleteSession
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