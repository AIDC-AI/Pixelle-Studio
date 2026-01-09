import { Form, Input, Modal, Select } from "antd"
import { mcpServerAPI } from "@/lib/mcpServerApi";
import { useEffect, useState } from "react";
import { useApp } from "@/context";
import { MCPServer } from "@/types/server";

interface IProps {
    open: boolean
    server?: MCPServer | null
    onSuccess?: () => void // 添加成功回调
    onClose?: () => void   // 关闭回调
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
    const { open, server, onSuccess, onClose } = props;
    const { messageApi } = useApp()

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
            messageApi.success('Successed!', 1)
            onSuccess?.()  // 调用成功回调
            handleCancel()
        }
    };

    const handleCancel = () => {
        form?.resetFields();
        setSelectedTransport('');
        onClose?.()
    };

    return <Modal
        title={`${!!server ? "Update Server" : "Add Server"}`}
        closable={{ 'aria-label': 'Custom Close Button' }}
        open={open}
        onOk={handleOk}
        onCancel={handleCancel}
        width="30%"
        destroyOnHidden
    >
        <Form
            name="server"
            form={form}
            autoComplete="off"
            layout="vertical"
            classNames={{
                label: "block text-sm font-medium text-gray-700",
            }}
        >
            <Form.Item<FieldType>
                label="名称"
                name="name"
                rules={[{ required: true, message: 'please input server name!' }]}
            >
                <Input size='large' placeholder="e.g., My MCP Server" allowClear />
            </Form.Item>

            <Form.Item<FieldType>
                label="传输类型"
                name="transport"
                rules={[{ required: true, message: 'Please select connection type!' }]}
            >
                <Select size='large' options={connectionTypes} onChange={(value) => setSelectedTransport(value)} />
            </Form.Item>

            {
                (selectedTransport === 'streamable-http' || selectedTransport === 'sse') && (<>
                    <Form.Item<FieldType>
                        label="服务器 URL"
                        name="url"
                        rules={[{ required: true, message: 'please input endpoint url!' }]}
                    >
                        <Input size='large' placeholder="https://api.example.com/mcp" allowClear />
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
                            size='large'
                            className="h-32 resize-none"
                            placeholder='Enter headers as JSON object, e.g. {"Authorization": "Bearer token"}' 
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
                        <Input size='large' placeholder="npx" allowClear />
                    </Form.Item>
                    <Form.Item<FieldType>
                        label="参数"
                        name="args"
                        rules={[{ required: true, message: 'please input arguments!' }]}
                    >
                        <Input size='large' placeholder="-y, @modelcontextprotocol/server-everything" allowClear />
                    </Form.Item>
                </>)
            }
        </Form>
    </Modal>
}

export default ToolConfigureModal