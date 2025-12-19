import { Button, Form, FormProps, Input, Modal, Select } from "antd"
import { MCPServer, mcpServerAPI } from "@/lib/mcpConfig";
import { useEffect, useState } from "react";
import { useApp } from "@/context";

interface IProps {
    open: boolean
    setOpen: React.Dispatch<React.SetStateAction<boolean>>
    server?: MCPServer | null
}

type FieldType = {
    name?: string;
    type?: string;
    endpoint?: string;
    url?: string;
    command?: string;
    args?: string;
    headers?: string;
};

const connectionTypes = [
    { label: 'HTTP (Streamable)', value: 'http' },
    { label: 'SSE (Server-Sent Events)', value: 'sse' },
    { label: 'Stdio', value: 'stdio' },
];

const McpConfigureModal: React.FC<IProps> = (props) => {
    const { open, setOpen, server } = props;
    const { config, setConfig, messageApi } = useApp()

    const [form] = Form.useForm();

    const [selectedType, setSelectedType] = useState<string>('');

    useEffect(() => {
        if (server) {
            form?.setFieldsValue({
                ...server,
                ...server?.config
            });
            setSelectedType(server.type);
        }
    }, [server]);

    const handleOk = async () => {
        const values = await form.validateFields();
        let serverConfig = {}
        if (values.type === 'http') {
            serverConfig = {
                endpoint: values.endpoint
            }
        } else if (values.type === 'sse') {
            serverConfig = {
                url: values.url
            }
        } else if (values.type === 'stdio') {
            serverConfig = {
                command: values.command,
                args: values.args,
            }
        }
        const serverToSave: Partial<MCPServer> = {
            name: values.name,
            type: values.type,
            config: serverConfig,
            enabled: true
        };
        if (!!values.headers && values.headers !== '') {
            serverToSave.headers = JSON.parse(values.headers);
        }
        if (!!server?.id) {
            serverToSave.id = server.id;
            mcpServerAPI.updateServer(server.id, serverToSave);
            setConfig({ servers: config.servers.map(s => s.id === server.id ? { ...s, ...serverToSave } : s) });
        } else {
            const newServer = mcpServerAPI.addServer(serverToSave as Omit<MCPServer, 'id'>);
            setConfig({ servers: [...config.servers, newServer] });
        }
        messageApi.success('Successed!', 1)
        handleCancel()
    };

    const handleCancel = () => {
        form?.resetFields();
        setSelectedType('');
        setOpen(false);
    };

    return <Modal
        title={`${!!server ? "Update Server" : "Add Server"}`}
        closable={{ 'aria-label': 'Custom Close Button' }}
        open={open}
        onOk={handleOk}
        onCancel={handleCancel}
        width="50%"
        destroyOnHidden
    >
        <Form
            name="server"
            form={form}
            labelCol={{ span: 8 }}
            autoComplete="off"
        >
            <Form.Item<FieldType>
                label="Server Name"
                name="name"
                rules={[{ required: true, message: 'please input server name!' }]}
            >
                <Input placeholder="e.g., My MCP Server" size="small" allowClear />
            </Form.Item>

            <Form.Item<FieldType>
                label="Connection Type"
                name="type"
                rules={[{ required: true, message: 'Please select connection type!' }]}
            >
                <Select options={connectionTypes} onChange={(value) => setSelectedType(value)} />
            </Form.Item>

            {
                selectedType === 'http' && (<>
                    <Form.Item<FieldType>
                        label="Endpoint URL"
                        name="endpoint"
                        rules={[{ required: true, message: 'please input endpoint url!' }]}
                    >
                        <Input placeholder="https://api.example.com/mcp" size="small" allowClear />
                    </Form.Item>
                    <Form.Item<FieldType>
                        label="Headers"
                        name="headers"
                        rules={[
                            ({ }) => ({
                                validator(_, value) {
                                    if (!value || value === '')
                                        return Promise.resolve();
                                    try {
                                        JSON.parse(value);
                                        return Promise.resolve();
                                    } catch (e) {
                                        return Promise.reject(new Error('Headers JSON format is invalid. Please check and try again!'));
                                    }
                                },
                            })
                        ]}
                    >
                        <Input.TextArea 
                            className="h-64"
                            placeholder='Enter headers as JSON object, e.g. {"Authorization": "Bearer token"}' 
                            size="small" 
                            allowClear 
                        />
                    </Form.Item>
                </>)
            }

            {
                selectedType === 'sse' && (<>
                    <Form.Item<FieldType>
                        label="SSE URL"
                        name="url"
                        rules={[{ required: true, message: 'please input sse url!' }]}
                    >
                        <Input placeholder="https://api.example.com/events" size="small" allowClear />
                    </Form.Item>
                    <Form.Item<FieldType>
                        label="Headers"
                        name="headers"
                        rules={[
                            ({ }) => ({
                                validator(_, value) {
                                    if (!value || value === '')
                                        return Promise.resolve();
                                    try {
                                        JSON.parse(value);
                                        return Promise.resolve();
                                    } catch (e) {
                                        return Promise.reject(new Error('Headers JSON format is invalid. Please check and try again!'));
                                    }
                                },
                            })
                        ]}
                    >
                        <Input.TextArea 
                            className="h-32"
                            placeholder='Enter headers as JSON object, e.g. {"Authorization": "Bearer token"}' 
                            size="small" 
                            allowClear 
                        />
                    </Form.Item>
                </>)
            }

            {
                selectedType === 'stdio' && (<>
                    <Form.Item<FieldType>
                        label="Command"
                        name="command"
                        rules={[{ required: true, message: 'please input command!' }]}
                    >
                        <Input placeholder="npx" size="small" allowClear />
                    </Form.Item>
                    <Form.Item<FieldType>
                        label="Arguments"
                        name="args"
                        rules={[{ required: true, message: 'please input arguments!' }]}
                    >
                        <Input placeholder="-y, @modelcontextprotocol/server-everything" size="small" allowClear />
                    </Form.Item>
                </>)
            }
        </Form>
    </Modal>
}

export default McpConfigureModal