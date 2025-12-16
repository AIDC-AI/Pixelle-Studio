import { useEffect, useMemo, useState } from "react"
import { useApp } from "../../context";
import { Button, Popconfirm, Table, TableColumnsType, Tag } from "antd";
import { MCPServer, mcpServerAPI } from "@/lib/mcpConfig";
import McpConfigureModal from "../ui/mcpConfigureModal";

interface Tool {
    name: string;
    description: string;
}

interface DataType {
    key: string;
    name: string;
    type: string;
    tools: Tool[];
}

const McpServers = () => {
    const { config, setConfig } = useApp()

    const [serverTools, setServerTools] = useState<Record<string, Tool[]>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [open, setOpen] = useState<boolean>(false);
    const [currentServer, setCurrentServer] = useState<MCPServer | null>(null);

    const fetchServerTools = async () => {
        setLoading(true);

        for (const server of config.servers) {
            if (!server.enabled) continue;

            try {
                const response = await fetch('http://localhost:8001/api/tools', {
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
            }
        }

        setLoading(false);
    };

    const handleDeleteServer = (id: string) => {
        mcpServerAPI.deleteServer(id);
        setConfig({ servers: config.servers.filter(s => s.id !== id) });
    };

    const servers = useMemo(() => {
        return config.servers.map(server => ({
            key: server.id,
            name: server.name,
            type: server.type,
            tools: serverTools[server.id] || []
        }))
    }, [config.servers, serverTools])

    useEffect(() => {
        fetchServerTools()
    }, [config.servers])

    const columns: TableColumnsType<DataType> = [
        {
            title: 'Name',
            dataIndex: 'name',
            width: '15%',
            ellipsis: true,
        },
        {
            title: 'Type',
            dataIndex: 'type',
            width: '15%',
            ellipsis: true,
            render: (type: string) => <Tag>{type.toUpperCase()}</Tag>
        },
        {
            title: 'Tools',
            dataIndex: 'tools',
            render: (tools: Tool[]) => <ul style={{ fontSize: '0.8em', margin: '0', paddingLeft: '20px' }}>
                {tools.map((tool, idx) => (
                    <li key={idx} style={{ marginBottom: '3px' }}>
                        <strong>{tool.name}:</strong>
                        <br />
                        {tool.description && (
                            <span style={{ color: '#666' }}>{tool.description}</span>
                        )}
                    </li>
                ))}
            </ul>
        },
        {
            title: 'Action',
            key: 'operation',
            align: 'center',
            render: (record: DataType) => <div className="flex flex-wrap gap-2 justify-center">
                <Button
                    type="primary"
                    size="small"
                    onClick={() => {
                        setCurrentServer(config.servers.find(s => s.id === record.key) || null)
                        setOpen(true)
                    }}
                >
                    Edit
                </Button>
                <Popconfirm
                    placement="top"
                    title={"Are you sure to delete this server?"}
                    description={"Delete this server"}
                    okText="Yes"
                    cancelText="No"
                    onConfirm={() => {
                        handleDeleteServer(record.key)
                    }}
                >
                    <Button
                        type="primary"
                        danger
                        size="small"
                    >
                        Delete
                    </Button>
                </Popconfirm>
            </div>
        },
    ];

    return <div
        className="w-full"
        onClick={(e) => {
            e.stopPropagation();
        }}
    >
        <div className="flex justify-end mb-4">
            <Button
                type="primary"
                onClick={() => {
                    setCurrentServer(null)
                    setOpen(true)
                }}
            >
                Add Mcp Server
            </Button>
        </div>
        <Table<DataType>
            rowSelection={{
                type: 'checkbox',
                selectedRowKeys: config.servers.filter(s => s.enabled).map(s => s.id),
                onChange: (keys, selectedRows) => {
                    console.log(keys, selectedRows)
                    for (const server in config.servers) {
                        if (selectedRows.findIndex((row) => row.key === config.servers[server].id) > -1) {
                            config.servers[server].enabled = true;
                        } else {
                            config.servers[server].enabled = false;
                        }
                    }
                    setConfig({
                        ...config
                    });
                }
            }}
            columns={columns}
            dataSource={servers}
            loading={loading}
            bordered
            size="small"
        />
        <McpConfigureModal
            open={open}
            setOpen={setOpen}
            server={currentServer}
        />
    </div>
}

export default McpServers