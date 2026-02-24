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

import { useState, useCallback, useEffect, useRef } from 'react';
import { mcpServerAPI, ConnectionStatus, ToolsResponse } from '@/lib/mcpServerApi';
import { MCPTool } from '@/types/server';

interface UseMCPServerOptions {
  autoCheckStatus?: boolean;  // Whether to auto-check status
  statusInterval?: number;    // Status check interval (milliseconds)
  autoLoadTools?: boolean;    // Whether to auto-load tools
}

interface MCPServerState {
  // Tool related
  tools: MCPTool[];
  toolsLoading: boolean;
  toolsError: string | null;
  
  // Status related
  status: ConnectionStatus | null;
  statusLoading: boolean;
  statusError: string | null;
  
  // Server info
  serverInfo: { id: string; name: string } | null;
  
  // Convenience states
  isConnected: boolean;
  isDisconnected: boolean;
  hasError: boolean;
}

export function useMCPServer(serverId?: string, options: UseMCPServerOptions = {}) {
  const {
    autoCheckStatus = false,
    statusInterval = 30000,
    autoLoadTools = false
  } = options;

  // Tool state
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);

  // Connection status
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Server info
  const [serverInfo, setServerInfo] = useState<{ id: string; name: string } | null>(null);

  // Timer reference
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch tool list (from status endpoint)
  const fetchTools = useCallback(async (id?: string) => {
    const targetId = id || serverId;
    if (!targetId) {
      setToolsError('No server ID provided');
      return null;
    }

    try {
      setToolsLoading(true);
      setToolsError(null);

      // Call status endpoint to get both status and tools
      const statusData = await mcpServerAPI.checkServerStatus(targetId);

      setTools(statusData.tools);
      setStatus(statusData);
      setServerInfo({
        id: statusData.server_id,
        name: statusData.server_name
      });

      return statusData.tools;
    } catch (err) {
      const errorMessage = (err as Error).message;
      setToolsError(errorMessage);
      setTools([]);
      throw err;
    } finally {
      setToolsLoading(false);
    }
  }, [serverId]);

  // Check connection status (also fetches tools)
  const checkStatus = useCallback(async (id?: string) => {
    const targetId = id || serverId;
    if (!targetId) {
      setStatusError('No server ID provided');
      return null;
    }

    try {
      setStatusLoading(true);
      setStatusError(null);

      const statusData = await mcpServerAPI.checkServerStatus(targetId);
      setStatus(statusData);
      
      // Also update tool list
      setTools(statusData.tools);

      // If server info not yet available, get it from status
      if (!serverInfo) {
        setServerInfo({
          id: statusData.server_id,
          name: statusData.server_name
        });
      }

      return statusData;
    } catch (err) {
      const errorMessage = (err as Error).message;
      setStatusError(errorMessage);
      setStatus(null);
      return null;
    } finally {
      setStatusLoading(false);
    }
  }, [serverId, serverInfo]);

  // Refresh all data (status + tools)
  const refresh = useCallback(async (id?: string) => {
    const targetId = id || serverId;
    if (!targetId) return;

    const [statusResult, toolsResult] = await Promise.allSettled([
      checkStatus(targetId),
      fetchTools(targetId)
    ]);

    return {
      status: statusResult.status === 'fulfilled' ? statusResult.value : null,
      tools: toolsResult.status === 'fulfilled' ? toolsResult.value : null
    };
  }, [serverId, checkStatus, fetchTools]);

  // Clear data
  const clear = useCallback(() => {
    setTools([]);
    setStatus(null);
    setServerInfo(null);
    setToolsError(null);
    setStatusError(null);
  }, []);

  // Stop auto-check
  const stopAutoCheck = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Start auto-check
  const startAutoCheck = useCallback(() => {
    if (serverId && !intervalRef.current) {
      checkStatus();
      intervalRef.current = setInterval(() => {
        checkStatus();
      }, statusInterval);
    }
  }, [serverId, statusInterval, checkStatus]);

  // Auto-load tools
  useEffect(() => {
    if (autoLoadTools && serverId) {
      fetchTools();
    }
  }, [autoLoadTools, serverId, fetchTools]);

  // Auto-check status
  useEffect(() => {
    if (autoCheckStatus && serverId) {
      // Check immediately
      checkStatus();

      // Set up periodic check
      intervalRef.current = setInterval(() => {
        checkStatus();
      }, statusInterval);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoCheckStatus, serverId, statusInterval, checkStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAutoCheck();
    };
  }, [stopAutoCheck]);

  // Compute convenience states
  const isConnected = status?.status === 'connected';
  const isDisconnected = status?.status === 'disconnected';
  const hasError = status?.status === 'error';

  return {
    // Tool related
    tools,
    toolsLoading,
    toolsError,
    fetchTools,

    // Status related
    status,
    statusLoading,
    statusError,
    checkStatus,

    // Server info
    serverInfo,

    // Convenience states
    isConnected,
    isDisconnected,
    hasError,

    // Combined operations
    refresh,
    clear,
    startAutoCheck,
    stopAutoCheck,

    // Loading state
    loading: toolsLoading || statusLoading,
    error: toolsError || statusError
  };
}
