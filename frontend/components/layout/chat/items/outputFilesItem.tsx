'use client';

import { OutputFile } from '@/types/message';
import { Download, FileSpreadsheet, FileImage, FileText, File, FolderDown } from 'lucide-react';

interface IProps {
    files: OutputFile[];
}

// Get icon based on file extension
const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
        case 'xlsx':
        case 'xls':
        case 'csv':
            return <FileSpreadsheet className="w-5 h-5" />;
        case 'png':
        case 'jpg':
        case 'jpeg':
        case 'gif':
        case 'webp':
        case 'svg':
            return <FileImage className="w-5 h-5" />;
        case 'pdf':
        case 'doc':
        case 'docx':
        case 'txt':
        case 'md':
            return <FileText className="w-5 h-5" />;
        default:
            return <File className="w-5 h-5" />;
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
            return 'Excel 文件';
        case 'csv':
            return 'CSV 文件';
        case 'png':
        case 'jpg':
        case 'jpeg':
        case 'gif':
        case 'webp':
            return '图片';
        case 'svg':
            return 'SVG 图片';
        case 'pdf':
            return 'PDF 文档';
        case 'doc':
        case 'docx':
            return 'Word 文档';
        case 'txt':
            return '文本文件';
        case 'md':
            return 'Markdown';
        default:
            return '文件';
    }
};

const OutputFilesItem: React.FC<IProps> = ({ files }) => {
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

    return (
        <div className="bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 rounded-2xl border-2 border-emerald-200 shadow-lg overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-emerald-500 to-teal-500 px-5 py-4">
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm">
                        <FolderDown className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h3 className="text-white font-bold text-lg">生成的文件</h3>
                        <p className="text-emerald-100 text-sm">
                            共 {files.length} 个文件可供下载
                        </p>
                    </div>
                </div>
            </div>

            {/* File List */}
            <div className="p-4 space-y-3">
                {files.map((file, index) => (
                    <div
                        key={index}
                        className="group flex items-center justify-between p-4 bg-white rounded-xl border border-emerald-100 hover:border-emerald-300 hover:shadow-md transition-all cursor-pointer"
                        onClick={() => handleDownload(file)}
                    >
                        <div className="flex items-center gap-4">
                            {/* File Icon */}
                            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 text-emerald-600 group-hover:from-emerald-200 group-hover:to-teal-200 transition-colors">
                                {getFileIcon(file.file_name)}
                            </div>
                            
                            {/* File Info */}
                            <div className="flex flex-col">
                                <span className="font-semibold text-slate-800 group-hover:text-emerald-700 transition-colors">
                                    {file.file_name}
                                </span>
                                <div className="flex items-center gap-2 text-sm text-slate-500">
                                    <span>{getFileTypeLabel(file.file_name)}</span>
                                    <span>•</span>
                                    <span>{formatFileSize(file.file_size)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Download Button */}
                        <button
                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg opacity-0 group-hover:opacity-100 hover:from-emerald-600 hover:to-teal-600 transition-all shadow-lg shadow-emerald-500/25"
                            onClick={(e) => {
                                e.stopPropagation();
                                handleDownload(file);
                            }}
                        >
                            <Download className="w-4 h-4" />
                            <span className="font-medium">下载</span>
                        </button>
                    </div>
                ))}
            </div>

            {/* Download All Button (if multiple files) */}
            {files.length > 1 && (
                <div className="px-4 pb-4">
                    <button
                        className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl hover:from-emerald-600 hover:to-teal-600 transition-all shadow-lg shadow-emerald-500/25 font-medium"
                        onClick={() => files.forEach(file => handleDownload(file))}
                    >
                        <FolderDown className="w-5 h-5" />
                        下载全部文件
                    </button>
                </div>
            )}
        </div>
    );
};

export default OutputFilesItem;

