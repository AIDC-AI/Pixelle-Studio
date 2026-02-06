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

/**
 * 聊天记录存储工具
 * 使用 IndexedDB (idb) 进行本地缓存
 */

import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { Message } from '@/types/message';
import { Session } from '@/types/session';

const DB_NAME = 'ChatDB';
const DB_VERSION = 1;

// 定义数据库结构
interface ChatDB extends DBSchema {
  messages: {
    key: string;
    value: StoredMessage;
    indexes: {
      'by-session': string;
      'by-timestamp': number;
    };
  };
  sessions: {
    key: string;
    value: Session;
    indexes: {
      'by-timestamp': number;
    };
  };
}

// 存储的消息类型（包含 id 和 sessionId）
export interface StoredMessage extends Message {
  id: string;
  sessionId: string;
}

class ChatStorage {
  private dbPromise: Promise<IDBPDatabase<ChatDB>> | null = null;

  /**
   * 获取数据库实例
   */
  private async getDB(): Promise<IDBPDatabase<ChatDB>> {
    if (!this.dbPromise) {
      this.dbPromise = openDB<ChatDB>(DB_NAME, DB_VERSION, {
        upgrade(db) {
          // 创建消息存储
          if (!db.objectStoreNames.contains('messages')) {
            const messageStore = db.createObjectStore('messages', { keyPath: 'id' });
            messageStore.createIndex('by-session', 'sessionId');
            messageStore.createIndex('by-timestamp', 'timestamp');
          }

          // 创建会话存储
          if (!db.objectStoreNames.contains('sessions')) {
            const sessionStore = db.createObjectStore('sessions', { keyPath: 'id' });
            sessionStore.createIndex('by-timestamp', 'timestamp');
          }
        },
      });
    }
    return this.dbPromise;
  }

  // ==================== 消息操作 ====================

  /**
   * 保存单条消息
   */
  async saveMessage(sessionId: string, message: Message, messageId?: string): Promise<void> {
    const db = await this.getDB();
    const messageWithMeta: StoredMessage = {
      ...message,
      id: messageId || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId,
    };
    await db.put('messages', messageWithMeta);
    
    // 更新会话时间戳
    await this.updateSessionTimestamp(sessionId);
  }

  /**
   * 批量保存消息
   */
  async saveMessages(sessionId: string, messages: Message[]): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('messages', 'readwrite');
    const timestamp = Date.now();

    await Promise.all([
      ...messages.map((message, index) =>
        tx.store.put({
          ...message,
          id: `msg_${timestamp}_${index}`,
          sessionId,
        } as StoredMessage)
      ),
      tx.done,
    ]);

    // 更新会话时间戳
    await this.updateSessionTimestamp(sessionId);
  }

  /**
   * 获取会话的所有消息
   */
  async getMessages(sessionId: string): Promise<Message[]> {
    const db = await this.getDB();
    const messages = await db.getAllFromIndex('messages', 'by-session', sessionId);
    return messages.sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * 获取会话的最新 N 条消息
   */
  async getRecentMessages(sessionId: string, limit: number = 50): Promise<Message[]> {
    const messages = await this.getMessages(sessionId);
    return messages.slice(-limit);
  }

  /**
   * 删除单条消息
   */
  async deleteMessage(messageId: string): Promise<void> {
    const db = await this.getDB();
    await db.delete('messages', messageId);
  }

  /**
   * 删除会话的所有消息
   */
  async deleteMessages(sessionId: string): Promise<void> {
    const db = await this.getDB();
    const messages = await db.getAllFromIndex('messages', 'by-session', sessionId);
    const tx = db.transaction('messages', 'readwrite');
    
    await Promise.all([
      ...messages.map((msg) => tx.store.delete(msg.id)),
      tx.done,
    ]);
  }

  /**
   * 清空所有消息
   */
  async clearAllMessages(): Promise<void> {
    const db = await this.getDB();
    await db.clear('messages');
  }

  // ==================== 会话操作 ====================

  /**
   * 创建新会话
   */
  async createSession(title: string = '新对话', backendSessionId?: string): Promise<Session> {
    const db = await this.getDB();
    const session: Session = {
      id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      title,
      timestamp: Date.now(),
      backendSessionId,
    };
    await db.put('sessions', session);
    return session;
  }

  /**
   * 获取所有会话
   */
  async getSessions(): Promise<Session[]> {
    const db = await this.getDB();
    const sessions = await db.getAllFromIndex('sessions', 'by-timestamp');
    return sessions.reverse(); // 最新的在前
  }

  /**
   * 获取单个会话
   */
  async getSession(sessionId: string): Promise<Session | undefined> {
    const db = await this.getDB();
    return db.get('sessions', sessionId);
  }

  /**
   * 更新会话标题
   */
  async updateSessionTitle(sessionId: string, title: string): Promise<void> {
    const db = await this.getDB();
    const session = await db.get('sessions', sessionId);
    if (session) {
      session.title = title;
      session.timestamp = Date.now();
      await db.put('sessions', session);
    }
  }

  /**
   * 更新会话的后端 ID
   */
  async updateSessionBackendId(sessionId: string, backendSessionId: string): Promise<void> {
    const db = await this.getDB();
    const session = await db.get('sessions', sessionId);
    if (session) {
      session.backendSessionId = backendSessionId;
      await db.put('sessions', session);
    }
  }

  /**
   * 更新会话时间戳（内部使用）
   */
  private async updateSessionTimestamp(sessionId: string): Promise<void> {
    const db = await this.getDB();
    const session = await db.get('sessions', sessionId);
    
    if (session) {
      session.timestamp = Date.now();
      await db.put('sessions', session);
    }
  }

  /**
   * 删除会话（包括所有消息）
   */
  async deleteSession(sessionId: string): Promise<void> {
    const db = await this.getDB();
    
    // 删除所有消息
    await this.deleteMessages(sessionId);
    
    // 删除会话
    await db.delete('sessions', sessionId);
  }

  /**
   * 清空所有会话和消息
   */
  async clearAll(): Promise<void> {
    const db = await this.getDB();
    await Promise.all([
      db.clear('messages'),
      db.clear('sessions'),
    ]);
  }

  // ==================== 工具方法 ====================

  /**
   * 获取数据库统计信息
   */
  async getStats(): Promise<{
    totalSessions: number;
    totalMessages: number;
    dbSize: string;
  }> {
    const db = await this.getDB();
    const sessions = await db.getAll('sessions');
    const messages = await db.getAll('messages');

    // 估算数据库大小
    const estimatedSize = JSON.stringify({ sessions, messages }).length;
    const sizeInMB = (estimatedSize / 1024 / 1024).toFixed(2);

    return {
      totalSessions: sessions.length,
      totalMessages: messages.length,
      dbSize: `${sizeInMB} MB`,
    };
  }

  /**
   * 获取会话的消息数量
   */
  async getMessageCount(sessionId: string): Promise<number> {
    const messages = await this.getMessages(sessionId);
    return messages.length;
  }

  /**
   * 导出所有数据（用于备份）
   */
  async exportData(): Promise<{
    sessions: Session[];
    messages: StoredMessage[];
  }> {
    const db = await this.getDB();
    const sessions = await db.getAll('sessions');
    const messages = await db.getAll('messages');
    return { sessions, messages };
  }

  /**
   * 导入数据（用于恢复）
   */
  async importData(data: {
    sessions: Session[];
    messages: StoredMessage[];
  }): Promise<void> {
    const db = await this.getDB();
    
    // 清空现有数据
    await this.clearAll();
    
    // 导入会话
    const sessionTx = db.transaction('sessions', 'readwrite');
    await Promise.all([
      ...data.sessions.map((session) => sessionTx.store.put(session)),
      sessionTx.done,
    ]);
    
    // 导入消息
    const msgTx = db.transaction('messages', 'readwrite');
    await Promise.all([
      ...data.messages.map((msg) => msgTx.store.put(msg)),
      msgTx.done,
    ]);
  }

  /**
   * 搜索消息
   */
  async searchMessages(keyword: string): Promise<Array<{ session: Session; message: StoredMessage }>> {
    const db = await this.getDB();
    const sessions = await db.getAll('sessions');
    const allMessages = await db.getAll('messages');
    
    const results: Array<{ session: Session; message: StoredMessage }> = [];
    
    for (const message of allMessages) {
      const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);
      if (content.toLowerCase().includes(keyword.toLowerCase())) {
        const session = sessions.find(s => s.id === message.sessionId);
        if (session) {
          results.push({ session, message });
        }
      }
    }
    
    return results;
  }
}

// 导出单例
export const chatStorage = new ChatStorage();
export default chatStorage;
