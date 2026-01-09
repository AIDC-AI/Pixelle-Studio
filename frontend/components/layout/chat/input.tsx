import { useApp } from "@/context"
import { API_BASE } from "@/lib/data"
import { Upload, UploadFile, UploadProps } from "antd"
import { Loader2, Plus, Send, Trash2, Square } from "lucide-react"

interface IProps {
    isProcessing?: boolean
    input?: string
    setInput?: React.Dispatch<React.SetStateAction<string>>
    fileList?: UploadFile[]
    setFileList?: React.Dispatch<React.SetStateAction<UploadFile[]>>
    handleSubmit?: () => void
    onStop?: () => void
}

const Input: React.FC<IProps> = (props) => {
    const { isProcessing, input, setInput, fileList = [], setFileList, handleSubmit, onStop } = props 

    const { user } = useApp()
    
    const beforeUpload = () => {
        if (fileList.length >= 5) {
            return Upload.LIST_IGNORE
        } 
        return true
    }
    
    const handleChange: UploadProps['onChange'] = (info) => {
        // info.fileList 已经是完整的文件列表，不需要再追加
        let newFileList = info.fileList.map((file) => {
            if (file.response) {
                file.url = file.response.url;
                // 存储本地文件路径，供 Agent 直接使用
                (file as any).filePath = file.response.file_path;
            }
            return file;
        });

        setFileList?.(newFileList);
    };
    
    return (
        <div className="px-4 pb-4">
            {/* Uploaded Files */}
            <div className="flex flex-col bg-white rounded-2xl border border-gray-200 shadow-sm">
                {fileList.length > 0 && (
                    <div className="flex flex-wrap p-2 gap-2 border-b border-gray-100">
                        {fileList.map((file, index) => (
                            <div
                                key={index}
                                className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 cursor-pointer border border-gray-200 hover:border-gray-300 transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    window.open(file.url, '_blank')
                                }}
                            >
                                <span className="font-medium">{file.name}</span>
                                {file?.size && <span className="text-gray-500 text-xs">({(file.size / 1024 / 1024).toFixed(2)}MB)</span>}
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        setFileList?.(files => files.filter((_, i) => i !== index))
                                    }}
                                    className="hover:text-red-500 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4"/>
                                </button>
                            </div>
                        ))}
                    </div>
                )}
                {/* Input Box */}
                <div className="flex h-25 items-center gap-2 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100 transition-all px-3 rounded-2xl">
                    <Upload
                        fileList={fileList}
                        action={`${API_BASE}/upload${!!user?.uid ? `?user_id=${user?.uid}`: ""}`}
                        onChange={handleChange}
                        beforeUpload={beforeUpload}
                        showUploadList={false}
                        multiple
                        disabled={isProcessing}
                    >
                        <button 
                            className="p-2.5 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors flex-shrink-0 border border-gray-200"
                            disabled={isProcessing}
                        >
                            <Plus className="w-5 h-5 text-gray-500" />
                        </button>
                    </Upload>
                    
                    <textarea
                        value={input}
                        onChange={(e) => setInput?.(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey && !isProcessing) {
                                e.preventDefault();
                                handleSubmit?.();
                            }
                        }}
                        placeholder="输入消息...（支持文本和文件）"
                        className="flex-1 h-full resize-none bg-transparent px-3 py-3 focus:outline-none text-gray-800 placeholder-gray-400"
                        rows={1}
                        disabled={isProcessing}
                    />
                    
                    {isProcessing ? (
                        <button
                            onClick={(e) => {
                                e.preventDefault()
                                onStop?.()
                            }}
                            className="p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all shrink-0 flex items-center gap-2"
                            title="停止推理"
                        >
                            <Square className="w-4 h-4 fill-current" />
                            <span className="text-sm font-medium">Stop</span>
                        </button>
                    ) : (
                        <button
                            onClick={(e) => {
                                e.preventDefault()
                                handleSubmit?.()
                            }}
                            disabled={(!input?.trim() && fileList.length === 0) || fileList.some(f => f.status === 'uploading')}
                            className="p-2.5 bg-gray-700 text-white rounded-xl hover:bg-gray-800 disabled:bg-gray-300 disabled:text-gray-400 disabled:cursor-not-allowed transition-all shrink-0"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default Input
