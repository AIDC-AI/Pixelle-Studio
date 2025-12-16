'use client'

import React, { createContext, useContext, useState } from 'react';
import { mcpServerAPI, type MCPServerConfig } from '../lib/mcpConfig';

type IProps = {
    config: MCPServerConfig
    setConfig: (config: MCPServerConfig) => void
};

const AppContext = createContext<IProps | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
    const [config, setConfig] = useState<MCPServerConfig>(mcpServerAPI.loadConfig());

    return <AppContext.Provider
        value={
            {
                config,
                setConfig
            }
        }
    >
        {children}
    </AppContext.Provider>;
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}