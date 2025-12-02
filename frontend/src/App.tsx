import { useState, useEffect, useRef } from 'react';
import './App.css';
import { api } from './api';
import { MCPConfigModal } from './components/MCPConfigModal';
import { mcpServerAPI, type MCPServerConfig } from './mcpConfig';

interface Message {
  type: 'user' | 'system' | 'log' | 'script' | 'result' | 'error';
  content: any;
  timestamp: number;
}

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentScript, setCurrentScript] = useState<string | null>(null);
  const [showMCPConfig, setShowMCPConfig] = useState(false);
  const [mcpConfig, setMCPConfig] = useState<MCPServerConfig>(mcpServerAPI.loadConfig());
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMsg = input;
    setInput('');
    setIsProcessing(true);
    setCurrentScript(null);

    // Add user message
    setMessages(prev => [...prev, { type: 'user', content: userMsg, timestamp: Date.now() }]);

    try {
      // 1. Create Chat (backend will auto-select tools)
      const { chat_id } = await api.createChat(userMsg, mcpConfig);

      // 2. Connect WebSocket
      const ws = new WebSocket(api.getWebSocketUrl(chat_id));

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'script') {
          setCurrentScript(data.content);
          setMessages(prev => [...prev, { type: 'system', content: 'Generated Workflow Script', timestamp: Date.now() }]);
        } else if (data.type === 'log') {
          // Append log to the last message if it's a log container, or create new
          // For simplicity, just add as message
          setMessages(prev => [...prev, { type: 'log', content: `[${data.stream || 'LOG'}] ${data.content}`, timestamp: Date.now() }]);
        } else if (data.type === 'result') {
          setMessages(prev => [...prev, { type: 'result', content: data.content, timestamp: Date.now() }]);
          setIsProcessing(false);
          ws.close();
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, { type: 'error', content: data.content, timestamp: Date.now() }]);
          setIsProcessing(false);
          ws.close();
        } else if (data.type === 'status') {
          setMessages(prev => [...prev, { type: 'system', content: data.content, timestamp: Date.now() }]);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setMessages(prev => [...prev, { type: 'error', content: 'Connection error', timestamp: Date.now() }]);
        setIsProcessing(false);
      };

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { type: 'error', content: 'Failed to start chat', timestamp: Date.now() }]);
      setIsProcessing(false);
    }
  };

  return (
    <>
      <MCPConfigModal
        isOpen={showMCPConfig}
        onClose={() => setShowMCPConfig(false)}
        onSave={(config) => {
          setMCPConfig(config);
          console.log('MCP config saved:', config);
        }}
      />

      <div className="app-header">
        <h1>MCP Workflow Demo</h1>
        <button className="config-btn" onClick={() => setShowMCPConfig(true)}>
          ⚙️ Configure MCP Servers
        </button>
      </div>

      <div className="container">
        <div className="main" style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
          <div className="chat-window">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.type}`}>
                {msg.type === 'user' && <div>{msg.content}</div>}
                {msg.type === 'system' && <div><em>{msg.content}</em></div>}
                {msg.type === 'log' && <div className="log-entry">{msg.content}</div>}
                {msg.type === 'result' && (
                  <div>
                    <strong>Result:</strong>
                    <pre>{JSON.stringify(msg.content, null, 2)}</pre>
                  </div>
                )}
                {msg.type === 'error' && <div style={{ color: 'red' }}>Error: {msg.content}</div>}
              </div>
            ))}
            {currentScript && (
              <div className="message system">
                <strong>Current Workflow Script:</strong>
                <div className="script-preview">{currentScript}</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="input-area" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your task..."
              disabled={isProcessing}
            />
            <button type="submit" disabled={isProcessing}>
              {isProcessing ? 'Processing...' : 'Send'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

export default App;
