/*
 * Copyright (C) 2026 AIDC-AI
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *     http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { mcpServerAPI, ConnectionStatus, ToolsResponse } from '@/lib/mcpServerApi';
import { MCPTool } from '@/types/server';

interface UseMCPServerOptions {
  autoCheckStatus?: boolean;  // 是否自动检查状态
  statusInterval?: number;    // 状态检查间隔（毫秒）
  autoLoadTools?: boolean;    // 是否自动加载工具
}

interface MCPServerState {
  // 工具相关
  tools: MCPTool[];
  toolsLoading: boolean;
  toolsError: string | null;
  
  // 状态相关
  status: ConnectionStatus | null;
  statusLoading: boolean;
  statusError: string | null;
  
  // 服务器信息
  serverInfo: { id: string; name: string } | null;
  
  // 便捷状态
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

  // 工具状态
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);

  // 连接状态
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // 服务器信息
  const [serverInfo, setServerInfo] = useState<{ id: string; name: string } | null>(null);

  // 定时器引用
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 获取工具列表（从 status 接口获取）
  const fetchTools = useCallback(async (id?: string) => {
    const targetId = id || serverId;
    if (!targetId) {
      setToolsError('No server ID provided');
      return null;
    }

    try {
      setToolsLoading(true);
      setToolsError(null);

      // 调用 status 接口，同时获取状态和工具
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

  // 检查连接状态（同时获取工具）
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
      
      // 同时更新工具列表
      setTools(statusData.tools);

      // 如果还没有服务器信息，从状态中获取
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

  // 刷新所有数据（状态 + 工具）
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

  // 清除数据
  const clear = useCallback(() => {
    setTools([]);
    setStatus(null);
    setServerInfo(null);
    setToolsError(null);
    setStatusError(null);
  }, []);

  // 停止自动检查
  const stopAutoCheck = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // 开始自动检查
  const startAutoCheck = useCallback(() => {
    if (serverId && !intervalRef.current) {
      checkStatus();
      intervalRef.current = setInterval(() => {
        checkStatus();
      }, statusInterval);
    }
  }, [serverId, statusInterval, checkStatus]);

  // 自动加载工具
  useEffect(() => {
    if (autoLoadTools && serverId) {
      fetchTools();
    }
  }, [autoLoadTools, serverId, fetchTools]);

  // 自动检查状态
  useEffect(() => {
    if (autoCheckStatus && serverId) {
      // 立即检查一次
      checkStatus();

      // 设置定时检查
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

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      stopAutoCheck();
    };
  }, [stopAutoCheck]);

  // 计算便捷状态
  const isConnected = status?.status === 'connected';
  const isDisconnected = status?.status === 'disconnected';
  const hasError = status?.status === 'error';

  return {
    // 工具相关
    tools,
    toolsLoading,
    toolsError,
    fetchTools,

    // 状态相关
    status,
    statusLoading,
    statusError,
    checkStatus,

    // 服务器信息
    serverInfo,

    // 便捷状态
    isConnected,
    isDisconnected,
    hasError,

    // 综合操作
    refresh,
    clear,
    startAutoCheck,
    stopAutoCheck,

    // 加载状态
    loading: toolsLoading || statusLoading,
    error: toolsError || statusError
  };
}
