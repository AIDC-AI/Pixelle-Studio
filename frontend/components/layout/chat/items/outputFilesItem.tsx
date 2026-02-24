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

'use client';

import { OutputFile } from '@/types/message';
import { canPreviewFile } from '@/utils/utils';
import { Download, FileSpreadsheet, FileImage, FileText, File, FolderDown, Bot, Eye, FileCode } from 'lucide-react';

interface IProps {
    files: OutputFile[];
    onFilePreview?: (file: OutputFile) => void;
}

// Get icon based on file extension
const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
        case 'xlsx':
        case 'xls':
        case 'csv':
            return <FileSpreadsheet className="w-4 h-4" />;
        case 'png':
        case 'jpg':
        case 'jpeg':
        case 'gif':
        case 'webp':
        case 'svg':
            return <FileImage className="w-4 h-4" />;
        case 'html':
        case 'htm':
            return <FileCode className="w-4 h-4" />;
        case 'pdf':
        case 'doc':
        case 'docx':
        case 'txt':
        case 'md':
            return <FileText className="w-4 h-4" />;
        default:
            return <File className="w-4 h-4" />;
    }
};

// Format file size
const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Get file type label
const getFileTypeLabel = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
        case 'xlsx':
        case 'xls':
            return 'Excel';
        case 'csv':
            return 'CSV';
        case 'png':
        case 'jpg':
        case 'jpeg':
        case 'gif':
        case 'webp':
            return 'Image';
        case 'svg':
            return 'SVG';
        case 'html':
        case 'htm':
            return 'HTML';
        case 'pdf':
            return 'PDF';
        case 'doc':
        case 'docx':
            return 'Word';
        case 'txt':
            return 'Text';
        case 'md':
            return 'MD';
        default:
            return 'File';
    }
};

const OutputFilesItem: React.FC<IProps> = ({ files, onFilePreview }) => {
    if (!files || files.length === 0) return null;

    const handleDownload = (file: OutputFile) => {
        // Create a link and trigger download
        const link = document.createElement('a');
        link.href = file.file_url;
        link.download = file.file_name;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handlePreview = (file: OutputFile) => {
        if (onFilePreview && canPreviewFile(file.file_name)) {
            onFilePreview(file);
        }
    };

    return (
        <div className="flex gap-3">
            {/* Avatar */}
            <div className="shrink-0">
                <div className="w-8 h-8 rounded-xl bg-orange-500 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="bg-white rounded-2xl rounded-tl-sm border border-gray-200 overflow-hidden">
                    {/* Header */}
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                        <div className="flex items-center gap-2">
                            <FolderDown className="w-4 h-4 text-gray-600" />
                            <span className="text-sm font-medium text-gray-700">Generated Files</span>
                            <span className="text-xs text-gray-500">
                                Total {files.length}
                            </span>
                        </div>
                    </div>

                    {/* File List */}
                    <div className="p-3 space-y-2">
                        {files.map((file, index) => (
                            <div
                                key={index}
                                className="group flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-100 transition-all cursor-pointer"
                                onClick={() => canPreviewFile(file.file_name) ? handlePreview(file) : handleDownload(file)}
                            >
                                <div className="flex items-center gap-3 min-w-0 flex-1">
                                    {/* File Icon */}
                                    <div className="flex items-center justify-center w-8 h-8 rounded bg-gray-200 text-gray-600 shrink-0">
                                        {getFileIcon(file.file_name)}
                                    </div>
                                    
                                    {/* File Info */}
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-sm font-medium text-gray-800 truncate">
                                            {file.file_name}
                                        </span>
                                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                            <span>{getFileTypeLabel(file.file_name)}</span>
                                            <span>•</span>
                                            <span>{formatFileSize(file.file_size)}</span>
                                            {canPreviewFile(file.file_name) && (
                                                <>
                                                    <span>•</span>
                                                    <span className="text-orange-500">Previewable</span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-all">
                                    {canPreviewFile(file.file_name) && (
                                        <button
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 text-white text-xs rounded hover:bg-orange-600 transition-all"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handlePreview(file);
                                            }}
                                        >
                                            <Eye className="w-3 h-3" />
                                            Preview
                                        </button>
                                    )}
                                    <button
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 text-white text-xs rounded hover:bg-gray-800 transition-all"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDownload(file);
                                        }}
                                    >
                                        <Download className="w-3 h-3" />
                                        Download
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Download All Button (if multiple files) */}
                    {files.length > 1 && (
                        <div className="px-3 pb-3">
                            <button
                                className="w-full flex items-center justify-center gap-2 py-2 bg-gray-700 text-white text-sm rounded-lg hover:bg-gray-800 transition-all"
                                onClick={() => files.forEach(file => handleDownload(file))}
                            >
                                <FolderDown className="w-4 h-4" />
                                Download All
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default OutputFilesItem;
