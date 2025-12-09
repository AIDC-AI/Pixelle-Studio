import { useState, useEffect, useRef } from 'react';
import './App.css';
import { api } from './api';
import { MCPConfigModal } from './components/MCPConfigModal';
import { mcpServerAPI, type MCPServerConfig } from './mcpConfig';

interface Message {
  type: 'user' | 'system' | 'log' | 'script' | 'result' | 'error' | 'iteration' | 'evaluation' | 'advice';
  content: any;
  timestamp: number;
  iteration?: number;
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

        if (data.type === 'iteration_start') {
          setMessages(prev => [...prev, { 
            type: 'iteration', 
            content: `🔄 Starting iteration ${data.iteration}/${data.max_iterations}`, 
            timestamp: Date.now(),
            iteration: data.iteration
          }]);
        } else if (data.type === 'iteration_end') {
          const statusEmoji = data.status === 'success' ? '✅' : data.status === 'failed' ? '❌' : '🔁';
          setMessages(prev => [...prev, { 
            type: 'iteration', 
            content: `${statusEmoji} Iteration ${data.iteration} ${data.status}`, 
            timestamp: Date.now(),
            iteration: data.iteration
          }]);
        } else if (data.type === 'script') {
          setCurrentScript(data.content);
          setMessages(prev => [...prev, { 
            type: 'system', 
            content: `📝 Generated script (iteration ${data.iteration})`, 
            timestamp: Date.now(),
            iteration: data.iteration
          }]);
        } else if (data.type === 'log') {
          setMessages(prev => [...prev, { 
            type: 'log', 
            content: `[${data.stream || 'LOG'}] ${data.content}`, 
            timestamp: Date.now() 
          }]);
        } else if (data.type === 'evaluation_result') {
          const emoji = data.meets_requirement ? '✅' : '⚠️';
          setMessages(prev => [...prev, { 
            type: 'evaluation', 
            content: `${emoji} Evaluation (iteration ${data.iteration}): ${data.meets_requirement ? 'PASS' : 'FAIL'} (confidence: ${(data.confidence_score * 100).toFixed(0)}%)\nReason: ${data.reason}`, 
            timestamp: Date.now(),
            iteration: data.iteration
          }]);
        } else if (data.type === 'revision_advice') {
          setMessages(prev => [...prev, { 
            type: 'advice', 
            content: `💡 Revision advice (iteration ${data.iteration}):\n${data.advice.advice || JSON.stringify(data.advice, null, 2)}`, 
            timestamp: Date.now(),
            iteration: data.iteration
          }]);
        } else if (data.type === 'final_result') {
          // 最终结果 - 现在才关闭连接
          const emoji = data.status === 'success' ? '🎉' : '❌';
          setMessages(prev => [...prev, { 
            type: 'result', 
            content: `${emoji} Final result (${data.total_iterations} iterations): ${data.status}\n${data.result ? JSON.stringify(data.result, null, 2) : data.error || ''}`, 
            timestamp: Date.now() 
          }]);
          setIsProcessing(false);
          ws.close();
        } else if (data.type === 'result') {
          // 兼容旧的 result 消息（如果有的话）
          setMessages(prev => [...prev, { type: 'result', content: data.content, timestamp: Date.now() }]);
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
                {msg.type === 'iteration' && <div><strong>{msg.content}</strong></div>}
                {msg.type === 'log' && <div className="log-entry">{msg.content}</div>}
                {msg.type === 'evaluation' && <div style={{ background: '#f0f8ff', padding: '8px', borderRadius: '4px' }}><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</pre></div>}
                {msg.type === 'advice' && <div style={{ background: '#fffacd', padding: '8px', borderRadius: '4px' }}><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</pre></div>}
                {msg.type === 'result' && (
                  <div>
                    <strong>Result:</strong>
                    <pre>{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}</pre>
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
