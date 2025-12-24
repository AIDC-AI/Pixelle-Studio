import { Form, Input, Modal, Select } from "antd"
import { mcpServerAPI } from "@/lib/mcpServerApi";
import { useEffect, useState } from "react";
import { useApp } from "@/context";
import { MCPServer } from "@/types/server";

interface IProps {
    open: boolean
    setOpen: React.Dispatch<React.SetStateAction<boolean>>
    server?: MCPServer | null
}

type FieldType = {
    name?: string;
    transport?: string;
    url?: string;
    headers?: string;
    command?: string;
    args?: string;
};

const connectionTypes = [
    { label: 'Streamable HTTP (推荐)', value: 'streamable-http' },
    { label: 'SSE (Server-Sent Events)', value: 'sse' },
    { label: 'STUDIO（本地进程）', value: 'stdio' },
];

const ToolConfigureModal: React.FC<IProps> = (props) => {
    const { open, setOpen, server } = props;
    const { setMcpServers, messageApi } = useApp()

    const [form] = Form.useForm();

    const [selectedTransport, setSelectedTransport] = useState<string>('');

    useEffect(() => {
        if (server) {
            form?.setFieldsValue({
                ...server,
            });
            setSelectedTransport(server.transport);
        }
    }, [server]);

    const handleOk = async () => {
        const values = await form.validateFields();
        const res = await mcpServerAPI.createServer(values)
        if (!!res) {
            setMcpServers(prev => [...prev, res])
            messageApi.success('Successed!', 1)
            handleCancel()
        }
    };

    const handleCancel = () => {
        form?.resetFields();
        setSelectedTransport('');
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
                label="名称"
                name="name"
                rules={[{ required: true, message: 'please input server name!' }]}
            >
                <Input placeholder="e.g., My MCP Server" size="small" allowClear />
            </Form.Item>

            <Form.Item<FieldType>
                label="传输类型"
                name="transport"
                rules={[{ required: true, message: 'Please select connection type!' }]}
            >
                <Select options={connectionTypes} onChange={(value) => setSelectedTransport(value)} />
            </Form.Item>

            {
                (selectedTransport === 'streamable-http' || selectedTransport === 'sse') && (<>
                    <Form.Item<FieldType>
                        label="服务器 URL"
                        name="url"
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
                            className="h-32"
                            placeholder='Enter headers as JSON object, e.g. {"Authorization": "Bearer token"}' 
                            size="small" 
                            allowClear 
                        />
                    </Form.Item>
                </>)
            }

            {
                selectedTransport === 'stdio' && (<>
                    <Form.Item<FieldType>
                        label="命令"
                        name="command"
                        rules={[{ required: true, message: 'please input command!' }]}
                    >
                        <Input placeholder="npx" size="small" allowClear />
                    </Form.Item>
                    <Form.Item<FieldType>
                        label="参数"
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

export default ToolConfigureModal