// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { LIST_IGNORE, Upload, UploadFile } from "@/components/ui/upload"
import { ToastType, useApp } from "@/context"
import { API_BASE } from "@/lib/data"
import { Plus, Send, Trash2, Square } from "lucide-react"

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

    const { user, showToast } = useApp()
    
    const beforeUpload = () => {
        if (fileList.length >= 5) {
            showToast(ToastType.ERROR, LIST_IGNORE)
            return false
        } 
        return true
    }

    return (
        <div className="px-4 pb-4">
            {/* Uploaded Files */}
            <div className="flex flex-col bg-white rounded-2xl border border-gray-200 shadow-sm">
                {fileList.length > 0 && (
                    <div className="flex flex-wrap p-2 gap-2 border-b border-gray-100">
                        {fileList.map((file, index) => (
                            <div
                                key={index}
                                className={`relative overflow-hidden px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 cursor-pointer border border-gray-200 hover:border-gray-300 transition-colors 
                                    ${file.status === "error" ? "text-red-500" : "text-gray-700"}`
                                }
                                onClick={(e) => {
                                    e.stopPropagation()
                                    window.open(file.url, '_blank')
                                }}
                            >
                                {/* Progress background layer */}
                                {file.status === "uploading" && (
                                    <div
                                        className="absolute inset-0 z-1 bg-blue-100 transition-all duration-300"
                                        style={{ width: `${file.percent || 0}%` }}
                                    />
                                )}
                            
                                {/* Default background */}
                                <div className={`absolute inset-0 z-0 ${
                                    file.status === "error" ? "bg-red-50" : "bg-gray-100"
                                }`} />
                                
                                <div className="relative z-10 flex items-center gap-2 w-full">
                                    <span className="font-medium">{file.name}</span>
                                    {file?.size && <span className={`text-xs ${file.status === "error" ? "text-red-500" : "text-gray-500"}`}>({(file.size / 1024 / 1024).toFixed(2)}MB)</span>}
                                    {
                                        file.status !== "uploading" && <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                setFileList?.(files => files.filter((_, i) => i !== index))
                                            }}
                                            className="hover:text-red-500 transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4"/>
                                        </button>
                                    }
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                {/* Input Box */}
                <div className="flex h-25 items-center gap-2 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100 transition-all px-3 rounded-2xl">
                    <Upload
                        fileList={fileList}
                        onChange={({ fileList }) => setFileList?.(fileList)}
                        beforeUpload={beforeUpload}
                        customRequest={({ file, onProgress, onSuccess, onError }) => {
                            // Your upload logic
                            const formData = new FormData();
                            formData.append('file', file);
                            
                            fetch(`${API_BASE}/upload${!!user?.uid ? `?user_id=${user?.uid}`: ""}`, {
                                method: 'POST',
                                body: formData,
                            })
                            .then(res => res.json())
                            .then(data => onSuccess(data))
                            .catch(err => onError(err));
                        }}
                        showUploadList={false}
                    >
                        <button 
                            className="p-2.5 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors shrink-0 border border-gray-200"
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
                                if (e.nativeEvent.isComposing) {
                                    return;
                                }
                                e.preventDefault();
                                handleSubmit?.();
                            }
                        }}
                        placeholder="Type a message... (supports text and files)"
                        className="flex-1 h-full resize-none bg-transparent px-3 py-3 focus:ring-0! focus:outline-none! text-gray-800 placeholder-gray-400"
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
                            title="Stop inference"
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
