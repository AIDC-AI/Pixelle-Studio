import { mcpServerAPI } from "@/lib/mcpServerApi";
import { useEffect, useState } from "react";
import { ToastType, useApp } from "@/context";
import { MCPServer, TransportType } from "@/types/server";
import { Dialog, Form } from "radix-ui";
import { XCircle } from "lucide-react"
import FormInput from "./form/input";
import FormSelect from "./form/select";

interface IProps {
    open: boolean
    server?: MCPServer | null
    onSuccess?: () => void // 添加成功回调
    onClose?: () => void   // 关闭回调
}

interface ServerFormData {
    name: string
    transport: TransportType
    url?: string | null
    headers?: string | null
    command?: string | null
    args?: string | null
}

const connectionTypes = [
    { label: 'Streamable HTTP (推荐)', value: 'streamable-http' },
    { label: 'SSE (Server-Sent Events)', value: 'sse' },
    { label: 'STUDIO（本地进程）', value: 'stdio' },
];

const ToolConfigureModal: React.FC<IProps> = (props) => {
    const { open, server, onSuccess, onClose } = props;
    const { showToast } = useApp()

    // 初始化表单数据
    const [formData, setFormData] = useState<ServerFormData>({
        name: '',
        transport: 'streamable-http',
        url: null,
        headers: null,
        command: null,
        args: null
    })
    
    useEffect(() => {
        if (server) {
            setFormData({
                ...server
            })
        }
    }, [server]);

    const handleSubmit = async (data: any) => {
        // 只提取需要的字段
        const serverData: Partial<MCPServer> = {
            name: data.name,
            transport: data.transport,
            url: data.url || null,
            command: data.command || null,
            args: data.args || null,
        }
        
        const res = await mcpServerAPI.createServer(serverData as any)
        if (!!res) {
            showToast(ToastType.SUCCESS, `${!!server ? "编辑成功！" : "添加成功！"}`)
            onSuccess?.()  // 调用成功回调
            handleCancel()
        }
    };

    const handleCancel = () => {
        setFormData({
            name: '',
            transport: 'streamable-http',
            url: null,
            headers: null,
            command: null,
            args: null
        })
        onClose?.()
    };

    return <Dialog.Root
        open={open}
        onOpenChange={(o) => {
            if (!o) {
                onClose?.()
            }
        }}
    >
		<Dialog.Portal>
			<Dialog.Content 
                className="bg-white rounded-md shadow-lg fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-100 p-6 animate-[contentShow_150ms_cubic-bezier(0.16,1,0.3,1)] z-999"
                aria-describedby={undefined}
            >
				<div className="flex flex-row justify-between items-center">
                    <Dialog.Title className="font-semibold text-gray-900 text-[17px]">{!!server ? "编辑工具" : "添加工具"}</Dialog.Title>
                    <Dialog.Close asChild>
                        <button 
                            className="rounded-full flex justify-center items-center text-[rgba(0,0,0,0.45)] hover:text-[rgba(0,0,0,0.6)]" 
                            aria-label="Close"
                        >
                            <XCircle className="w-5 h-5"/>
                        </button>
                    </Dialog.Close>
                </div>
                <Form.Root 
                    id="toolForm"
                    onSubmit={async (e) => {
                        e.preventDefault();
                        const formData = new FormData(e.currentTarget)
                        const data = Object.fromEntries(formData)
                        await handleSubmit(data)
                    }}
                    className="flex flex-col flex-1 gap-4 mt-4 overflow-auto overscroll-contain"
                >
                    <FormInput 
                        name="name"
                        label="名称"
                        errorMessages={[
                            { match:"valueMissing", content:"请先输入工具名称" }
                        ]}
                        placeholder="工具名称"            
                        value={formData.name}
                        setValue={(value: string) => {
                            setFormData(prev => ({
                                ...prev,
                                name: value
                            }))
                        }}
                    />
                    <FormSelect 
                        name="transport"
                        label="传输类型"
                        errorMessages={[
                            { match:"valueMissing", content:"请先选择传输类型" }
                        ]}
                        selectOptions={connectionTypes}
                        setValue={(value: string) => {
                            setFormData(prev => ({
                                ...prev,
                                transport: value as TransportType
                            }))
                        }}
                    />
                    {
                        (formData.transport === 'streamable-http' || formData.transport === 'sse') && (
                            <>
                                <FormInput 
                                    name="url"
                                    label="服务器 URL"
                                    errorMessages={[
                                        { match:"valueMissing", content:"请先输入服务器URL" }
                                    ]}
                                    placeholder="服务器URL"
                                    value={formData.url || ''}
                                    setValue={(value: string) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            url: value
                                        }))
                                    }}
                                />
                                <FormInput 
                                    name="headers"
                                    label="Headers"
                                    required={false}
                                    placeholder="headers"
                                    isTextarea={true}
                                    isFlexMax={true}
                                    value={formData.headers || ''}
                                    setValue={(value: string) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            headers: value
                                        }))
                                    }}
                                />
                            </>
                        )
                    }
                    {
                        formData.transport === 'stdio' && (
                            <>
                                <FormInput 
                                    name="command"
                                    label="命令"
                                    errorMessages={[
                                        { match:"valueMissing", content:"请先输入命令" }
                                    ]}
                                    placeholder="命令"
                                    value={formData.command || ''}
                                    setValue={(value: string) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            command: value
                                        }))
                                    }}
                                />
                                <FormInput 
                                    name="args"
                                    label="参数"
                                    errorMessages={[
                                        { match:"valueMissing", content:"请先输入参数" }
                                    ]}
                                    placeholder="参数"
                                    value={formData.args || ''}
                                    setValue={(value: string) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            args: value
                                        }))
                                    }}
                                />
                            </>
                        )
                    }
                    <Form.Submit asChild>
                        <button className="inline-flex items-center justify-center rounded-lg px-3.75 text-[15px] leading-none font-medium h-8.75
                         w-full bg-white hover:bg-gray-100 text-gray-900 shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-gray-300 hover:border-gray-500">
                            提交
                        </button>
                    </Form.Submit>
                </Form.Root>
			</Dialog.Content>
		</Dialog.Portal>
	</Dialog.Root>
}

export default ToolConfigureModal