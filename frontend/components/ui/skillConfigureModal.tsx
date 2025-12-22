'use client'

import { useApp } from "@/context";
import { api } from "@/lib/api";
import { Form, Input, Modal } from "antd";
import { useEffect } from "react";

interface IProps {
    open: boolean
    setOpen: React.Dispatch<React.SetStateAction<boolean>>
    setSelectedIndex: React.Dispatch<React.SetStateAction<number>>
    skillName?: string
    reload?: () => void
}

type FieldType = {
    name?: string;
    content?: string
};

const SkillConfigureModal: React.FC<IProps> = (props) => {
    const { open, setOpen, skillName, reload, setSelectedIndex} = props;
    const { messageApi } = useApp()
    
    const [form] = Form.useForm();

    const handleGetSkillContent = async (name: string) => {
        if (!name || name === '') 
            return
        try {
            const response = await api.getSkillContent(name)
            if (!!response) {
                const content = response?.full_content || ''
                form?.setFieldsValue({
                    name: skillName,
                    content
                });
            }
        }
        catch (error) {
            console.error(`Failed to get skill ${name}:`, error);
        }
    }

    useEffect(() => {
        if (skillName) {
            handleGetSkillContent(skillName)
        }
    }, [skillName]);
    
    const handleOk = async () => {
        const values = await form.validateFields();
        try {
            const response = await api.createSkill(values.name, values.content)
            if (!!response) {
                messageApi.success('Successed!', 1)
                reload?.()
                handleCancel()
            }
        }
        catch (error) {
            console.error(`Failed to get skill ${name}:`, error);
        }
    }

    const handleCancel = () => {
        setSelectedIndex?.(-1)
        form?.resetFields()
        setOpen(false)
    }
    
    return <Modal
        title={`${(!!skillName && skillName !== '') ? 'Update Skill' : 'Add Skill'}`}
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
                label="Skill Name"
                name="name"
                rules={[{ required: true, message: 'please input skill name!' }]}
            >
                <Input placeholder="e.g., My MCP Server" size="small" allowClear />
            </Form.Item>

            <Form.Item<FieldType>
                label="Skill Content"
                name="content"
                rules={[{ required: true, message: 'please input skill content!' }]}
            >
                <Input.TextArea 
                    className="h-128"
                    placeholder='Enter skill content' 
                    size="small" 
                    allowClear 
                />
            </Form.Item>
        </Form>
    </Modal>
}

export default SkillConfigureModal