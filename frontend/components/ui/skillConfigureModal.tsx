'use client'

import { useApp } from "@/context";
import { api } from "@/lib/api";
import { Skill } from "@/types/skill";
import { Checkbox, Col, Drawer, Flex, Form, Input, Row } from "antd";
import { useEffect } from "react";

interface IProps {
    open: boolean
    skill?: Skill
    onSuccess?: () => void // 添加成功回调
    onClose?: () => void   // 关闭回调
}

type FieldType = {
    name?: string
    description?: string
    content?: string
};

const SkillConfigureModal: React.FC<IProps> = (props) => {
    const { open, skill, onSuccess, onClose} = props;
    const { messageApi } = useApp()
    
    const [form] = Form.useForm();

    useEffect(() => {
        if (!!skill) {
            form?.setFieldsValue({
                ...skill
            });
        }
    }, [skill]);
    
    const handleOk = async () => {
        const values = await form.validateFields();
        try {
            const response = await api.createSkill(values.name, values.content)
            if (!!response) {
                messageApi.success('Successed!', 1)
                onSuccess?.()
                handleCancel()
            }
        }
        catch (error) {
            console.error(`Failed to get skill ${name}:`, error);
        }
    }

    const handleCancel = () => {
        form?.resetFields()
        onClose?.()
    }
    
    return <Drawer
        title={`${!!skill ? 'Update Skill' : 'Add Skill'}`}
        placement="left"
        size={window.innerWidth / 2}
        closable={{ 'aria-label': 'Custom Close Button' }}
        open={open}
        onClose={handleCancel}
        destroyOnHidden
    >
        <Form
            name="server"
            form={form}
            layout="vertical"
            autoComplete="off"
        >
            <Form.Item<FieldType>
                label="名称（创建后不可修改）"
                name="name"
                rules={[{ required: true, message: 'please input skill name!' }]}
            >
                <Input placeholder="e.g., My Skill" allowClear />
            </Form.Item>

            <Form.Item<FieldType>
                label="描述"
                name="description"
                rules={[{ required: true, message: 'please input skill description!' }]}
            >
                <Input.TextArea 
                    placeholder="Enter skill description"
                    rows={3}
                    allowClear 
                    style={{ resize: 'none' }}
                />
            </Form.Item>

            {/* <Form.Item 
                label="脚本文件"
                name="scripts"
            >
                <Checkbox.Group>
                    <Flex wrap gap='small'>
                        {
                            scripts?.map((script) => <Checkbox 
                                key={`${script.serverId}-${script.toolName}`}
                                value={`${script.serverId}-${script.toolName}`}
                            >
                                <div
                                    className="items-center gap-2 p-2 rounded-lg border border-gray-200 transition-colors"
                                >
                                    <p className="text-sm text-gray-700 truncate">{script.toolName}</p>
                                    <p className="text-xs text-gray-500 truncate">{script.serverName}</p>
                                </div>
                            </Checkbox>)
                        }
                    </Flex>
                </Checkbox.Group>
            </Form.Item> */}

            <Form.Item<FieldType>
                label="详细内容（Markdown）"
                name="content"
                rules={[{ required: true, message: 'please input skill content!' }]}
            >
                <Input.TextArea 
                    placeholder='Enter skill content in Markdown format' 
                    allowClear
                    rows={24}
                />
            </Form.Item>
            
        </Form>
    </Drawer>
}

export default SkillConfigureModal