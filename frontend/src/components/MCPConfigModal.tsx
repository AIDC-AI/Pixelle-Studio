import { useState, useEffect } from 'react';
import { type MCPServer, mcpServerAPI, type MCPServerConfig } from '../mcpConfig';
import './MCPConfigModal.css';

interface Tool {
    name: string;
    description: string;
}

interface MCPConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (config: MCPServerConfig) => void;
}

export function MCPConfigModal({ isOpen, onClose, onSave }: MCPConfigModalProps) {
    const [config, setConfig] = useState<MCPServerConfig>(mcpServerAPI.loadConfig());
    const [editingServer, setEditingServer] = useState<Partial<MCPServer> | null>(null);
    const [isAdding, setIsAdding] = useState(false);
    const [serverTools, setServerTools] = useState<Record<string, Tool[]>>({});
    const [loadingTools, setLoadingTools] = useState<Record<string, boolean>>({});
    const [headersText, setHeadersText] = useState<string>('');

    // Fetch tools for each enabled server
    useEffect(() => {
        if (!isOpen) return;

        const fetchServerTools = async () => {
            for (const server of config.servers) {
                if (!server.enabled) continue;

                setLoadingTools(prev => ({ ...prev, [server.id]: true }));

                try {
                    const response = await fetch('http://localhost:8009/api/tools', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            servers: [server]
                        })
                    });

                    if (response.ok) {
                        const tools = await response.json();
                        setServerTools(prev => ({ ...prev, [server.id]: tools }));
                    }
                } catch (error) {
                    console.error(`Failed to fetch tools for ${server.name}:`, error);
                } finally {
                    setLoadingTools(prev => ({ ...prev, [server.id]: false }));
                }
            }
        };

        fetchServerTools();
    }, [config.servers, isOpen]);


    if (!isOpen) return null;

    const handleAddServer = () => {
        setIsAdding(true);
        setHeadersText('');
        setEditingServer({
            name: '',
            type: 'http',
            config: {},
            enabled: true
        });
    };

    const handleSaveServer = () => {
        if (!editingServer || !editingServer.name) return;

        // 保存时解析 headers
        let serverToSave = { ...editingServer };
        if (headersText.trim()) {
            try {
                serverToSave.headers = JSON.parse(headersText);
            } catch {
                alert('Headers JSON format is invalid. Please check and try again.');
                return;
            }
        }

        const newServer = mcpServerAPI.addServer(serverToSave as Omit<MCPServer, 'id'>);
        setConfig({ servers: [...config.servers, newServer] });
        setEditingServer(null);
        setIsAdding(false);
        setHeadersText('');
    };

    const handleDeleteServer = (id: string) => {
        mcpServerAPI.deleteServer(id);
        setConfig({ servers: config.servers.filter(s => s.id !== id) });
    };

    const handleToggleServer = (id: string, enabled: boolean) => {
        mcpServerAPI.updateServer(id, { enabled });
        setConfig({
            servers: config.servers.map(s =>
                s.id === id ? { ...s, enabled } : s
            )
        });
    };

    const handleSaveConfig = () => {
        mcpServerAPI.saveConfig(config);
        onSave(config);
        onClose();
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>MCP Server Configuration</h2>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body">
                    <div className="servers-list">
                        <h3>Configured Servers</h3>
                        {config.servers.length === 0 && (
                            <p className="empty-state">No MCP servers configured yet.</p>
                        )}
                        {config.servers.map(server => (
                            <div key={server.id} className="server-item">
                                <div className="server-info">
                                    <input
                                        type="checkbox"
                                        checked={server.enabled}
                                        onChange={(e) => handleToggleServer(server.id, e.target.checked)}
                                    />
                                    <div>
                                        <strong>{server.name}</strong>
                                        <span className="server-type">{server.type.toUpperCase()}</span>
                                    </div>
                                </div>
                                <button
                                    className="delete-btn"
                                    onClick={() => handleDeleteServer(server.id)}
                                >
                                    Delete
                                </button>

                                {/* Tools list for this server */}
                                {server.enabled && (
                                    <div className="server-tools" style={{ marginTop: '10px', paddingLeft: '30px' }}>
                                        {loadingTools[server.id] ? (
                                            <p style={{ fontSize: '0.85em', color: '#999' }}>Loading tools...</p>
                                        ) : serverTools[server.id] && serverTools[server.id].length > 0 ? (
                                            <>
                                                <p style={{ fontSize: '0.85em', fontWeight: 'bold', marginBottom: '5px' }}>
                                                    Tools ({serverTools[server.id].length}):
                                                </p>
                                                <ul style={{ fontSize: '0.8em', margin: '0', paddingLeft: '20px' }}>
                                                    {serverTools[server.id].map((tool, idx) => (
                                                        <li key={idx} style={{ marginBottom: '3px' }}>
                                                            <strong>{tool.name}</strong>
                                                            {tool.description && (
                                                                <span style={{ color: '#666' }}> - {tool.description}</span>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </>
                                        ) : (
                                            <p style={{ fontSize: '0.85em', color: '#999' }}>No tools available</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {isAdding && editingServer && (
                        <div className="add-server-form">
                            <h3>Add New Server</h3>
                            <div className="form-group">
                                <label>Server Name</label>
                                <input
                                    type="text"
                                    value={editingServer.name || ''}
                                    onChange={(e) => setEditingServer({ ...editingServer, name: e.target.value })}
                                    placeholder="e.g., My MCP Server"
                                />
                            </div>

                            <div className="form-group">
                                <label>Connection Type</label>
                                <select
                                    value={editingServer.type || 'http'}
                                    onChange={(e) => setEditingServer({
                                        ...editingServer,
                                        type: e.target.value as 'sse' | 'stdio' | 'http',
                                        config: {}
                                    })}
                                >
                                    <option value="http">HTTP (Streamable)</option>
                                    <option value="sse">SSE (Server-Sent Events)</option>
                                    <option value="stdio">stdio</option>
                                </select>
                            </div>

                            {editingServer.type === 'http' && (
                                <div className="form-group">
                                    <label>Endpoint URL</label>
                                    <input
                                        type="url"
                                        value={editingServer.config?.endpoint || ''}
                                        onChange={(e) => setEditingServer({
                                            ...editingServer,
                                            config: { ...editingServer.config, endpoint: e.target.value }
                                        })}
                                        placeholder="https://api.example.com/mcp"
                                    />
                                </div>
                            )}
                            {/* Headers 输入框 - 适用于 HTTP 和 SSE 类型 */}
                            {(editingServer.type === 'http' || editingServer.type === 'sse') && (
                                <div className="form-group">
                                    <label>Headers (JSON format)</label>
                                    <textarea
                                        value={headersText}
                                        onChange={(e) => setHeadersText(e.target.value)}
                                        onBlur={(e) => {
                                            // 失去焦点时尝试格式化 JSON
                                            try {
                                                if (e.target.value.trim()) {
                                                    const headers = JSON.parse(e.target.value);
                                                    setHeadersText(JSON.stringify(headers, null, 2));
                                                }
                                            } catch {
                                                // JSON 格式不正确，保持原样
                                            }
                                        }}
                                        placeholder='{"Authorization": "Bearer sk-xxx"}'
                                        rows={3}
                                        style={{ 
                                            width: '100%', 
                                            fontFamily: 'monospace',
                                            fontSize: '0.9em',
                                            resize: 'vertical'
                                        }}
                                    />
                                    <small style={{ color: '#888', fontSize: '0.8em' }}>
                                        Enter headers as JSON object, e.g. {`{"Authorization": "Bearer token"}`}
                                    </small>
                                </div>
                            )}
                            {editingServer.type === 'sse' && (
                                <div className="form-group">
                                    <label>SSE URL</label>
                                    <input
                                        type="url"
                                        value={editingServer.config?.url || ''}
                                        onChange={(e) => setEditingServer({
                                            ...editingServer,
                                            config: { ...editingServer.config, url: e.target.value }
                                        })}
                                        placeholder="https://api.example.com/events"
                                    />
                                </div>
                            )}

                            {editingServer.type === 'stdio' && (
                                <>
                                    <div className="form-group">
                                        <label>Command</label>
                                        <input
                                            type="text"
                                            value={editingServer.config?.command || ''}
                                            onChange={(e) => setEditingServer({
                                                ...editingServer,
                                                config: { ...editingServer.config, command: e.target.value }
                                            })}
                                            placeholder="npx"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Arguments (comma separated)</label>
                                        <input
                                            type="text"
                                            value={editingServer.config?.args?.join(', ') || ''}
                                            onChange={(e) => setEditingServer({
                                                ...editingServer,
                                                config: {
                                                    ...editingServer.config,
                                                    args: e.target.value.split(',').map(s => s.trim())
                                                }
                                            })}
                                            placeholder="-y, @modelcontextprotocol/server-everything"
                                        />
                                    </div>
                                </>
                            )}

                            <div className="form-actions">
                                <button onClick={() => { setIsAdding(false); setEditingServer(null); }}>
                                    Cancel
                                </button>
                                <button onClick={handleSaveServer} className="primary">
                                    Add Server
                                </button>
                            </div>
                        </div>
                    )}

                    {!isAdding && (
                        <button className="add-server-btn" onClick={handleAddServer}>
                            + Add MCP Server
                        </button>
                    )}
                </div>

                <div className="modal-footer">
                    <button onClick={onClose}>Cancel</button>
                    <button onClick={handleSaveConfig} className="primary">
                        Save Configuration
                    </button>
                </div>
            </div>
        </div>
    );
}
