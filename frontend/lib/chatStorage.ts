/**
 * Chat history storage utility
 * Uses IndexedDB (idb) for local caching
 */

import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { Message } from '@/types/message';
import { Session } from '@/types/session';

const DB_NAME = 'ChatDB';
const DB_VERSION = 1;

// Define database schema
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

// Stored message type (includes id and sessionId)
export interface StoredMessage extends Message {
  id: string;
  sessionId: string;
}

class ChatStorage {
  private dbPromise: Promise<IDBPDatabase<ChatDB>> | null = null;

  /**
   * Get database instance
   */
  private async getDB(): Promise<IDBPDatabase<ChatDB>> {
    if (!this.dbPromise) {
      this.dbPromise = openDB<ChatDB>(DB_NAME, DB_VERSION, {
        upgrade(db) {
          // Create message store
          if (!db.objectStoreNames.contains('messages')) {
            const messageStore = db.createObjectStore('messages', { keyPath: 'id' });
            messageStore.createIndex('by-session', 'sessionId');
            messageStore.createIndex('by-timestamp', 'timestamp');
          }

          // Create session store
          if (!db.objectStoreNames.contains('sessions')) {
            const sessionStore = db.createObjectStore('sessions', { keyPath: 'id' });
            sessionStore.createIndex('by-timestamp', 'timestamp');
          }
        },
      });
    }
    return this.dbPromise;
  }

  // ==================== Message Operations ====================

  /**
   * Save a single message
   */
  async saveMessage(sessionId: string, message: Message, messageId?: string): Promise<void> {
    const db = await this.getDB();
    const messageWithMeta: StoredMessage = {
      ...message,
      id: messageId || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId,
    };
    await db.put('messages', messageWithMeta);
    
    // Update session timestamp
    await this.updateSessionTimestamp(sessionId);
  }

  /**
   * Save messages in batch
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

    // Update session timestamp
    await this.updateSessionTimestamp(sessionId);
  }

  /**
   * Get all messages for a session
   */
  async getMessages(sessionId: string): Promise<Message[]> {
    const db = await this.getDB();
    const messages = await db.getAllFromIndex('messages', 'by-session', sessionId);
    return messages.sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Get the latest N messages for a session
   */
  async getRecentMessages(sessionId: string, limit: number = 50): Promise<Message[]> {
    const messages = await this.getMessages(sessionId);
    return messages.slice(-limit);
  }

  /**
   * Delete a single message
   */
  async deleteMessage(messageId: string): Promise<void> {
    const db = await this.getDB();
    await db.delete('messages', messageId);
  }

  /**
   * Delete all messages for a session
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
   * Clear all messages
   */
  async clearAllMessages(): Promise<void> {
    const db = await this.getDB();
    await db.clear('messages');
  }

  // ==================== Session Operations ====================

  /**
   * Create a new session
   */
  async createSession(title: string = 'New Chat', backendSessionId?: string): Promise<Session> {
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
   * Get all sessions
   */
  async getSessions(): Promise<Session[]> {
    const db = await this.getDB();
    const sessions = await db.getAllFromIndex('sessions', 'by-timestamp');
    return sessions.reverse(); // Most recent first
  }

  /**
   * Get a single session
   */
  async getSession(sessionId: string): Promise<Session | undefined> {
    const db = await this.getDB();
    return db.get('sessions', sessionId);
  }

  /**
   * Update session title
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
   * Update session backend ID
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
   * Update session timestamp (internal use)
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
   * Delete a session (including all messages)
   */
  async deleteSession(sessionId: string): Promise<void> {
    const db = await this.getDB();
    
    // Delete all messages
    await this.deleteMessages(sessionId);
    
    // Delete session
    await db.delete('sessions', sessionId);
  }

  /**
   * Clear all sessions and messages
   */
  async clearAll(): Promise<void> {
    const db = await this.getDB();
    await Promise.all([
      db.clear('messages'),
      db.clear('sessions'),
    ]);
  }

  // ==================== Utility Methods ====================

  /**
   * Get database statistics
   */
  async getStats(): Promise<{
    totalSessions: number;
    totalMessages: number;
    dbSize: string;
  }> {
    const db = await this.getDB();
    const sessions = await db.getAll('sessions');
    const messages = await db.getAll('messages');

    // Estimate database size
    const estimatedSize = JSON.stringify({ sessions, messages }).length;
    const sizeInMB = (estimatedSize / 1024 / 1024).toFixed(2);

    return {
      totalSessions: sessions.length,
      totalMessages: messages.length,
      dbSize: `${sizeInMB} MB`,
    };
  }

  /**
   * Get message count for a session
   */
  async getMessageCount(sessionId: string): Promise<number> {
    const messages = await this.getMessages(sessionId);
    return messages.length;
  }

  /**
   * Export all data (for backup)
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
   * Import data (for restore)
   */
  async importData(data: {
    sessions: Session[];
    messages: StoredMessage[];
  }): Promise<void> {
    const db = await this.getDB();
    
    // Clear existing data
    await this.clearAll();
    
    // Import sessions
    const sessionTx = db.transaction('sessions', 'readwrite');
    await Promise.all([
      ...data.sessions.map((session) => sessionTx.store.put(session)),
      sessionTx.done,
    ]);
    
    // Import messages
    const msgTx = db.transaction('messages', 'readwrite');
    await Promise.all([
      ...data.messages.map((msg) => msgTx.store.put(msg)),
      msgTx.done,
    ]);
  }

  /**
   * Search messages
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

// Export singleton
export const chatStorage = new ChatStorage();
export default chatStorage;
