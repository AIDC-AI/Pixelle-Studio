'use client';

import { X, FileText, Image, FileCode, File, ExternalLink, Download, Maximize2, Minimize2, RefreshCw, AlertCircle, FileSpreadsheet } from 'lucide-react';
import { useState, useEffect, lazy, Suspense } from 'react';
import { OutputFile } from '@/types/message';
import { API_BASE } from '@/lib/data';

// 动态导入 DataGrid（样式在 globals.css 中导入）
const DataGrid = lazy(() => import('react-data-grid').then(mod => ({ default: mod.DataGrid })));

interface IProps {
    file: OutputFile | null;
    onClose: () => void;
}

const FilePreview: React.FC<IProps> = ({ file, onClose }) => {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [iframeKey, setIframeKey] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [excelData, setExcelData] = useState<{ columns: any[]; rows: any[] } | null>(null);
    const [selectedSheet, setSelectedSheet] = useState<string>('');
    const [sheetNames, setSheetNames] = useState<string[]>([]);

    useEffect(() => {
        // 当文件改变时，重新加载
        setIframeKey(prev => prev + 1);
        setIsLoading(true);
        setLoadError(null);
        setExcelData(null);
        setSheetNames([]);
        setSelectedSheet('');
        
        // 如果是 Excel 文件，加载数据
        const ext = getFileExtension(file?.file_name || '');
        if (file && (ext === 'xlsx' || ext === 'xls' || ext === 'csv')) {
            loadExcelFile(getFullUrl(file.file_url));
        }
    }, [file?.file_url]);

    if (!file) return null;

    const getFileExtension = (filename: string): string => {
        return filename.split('.').pop()?.toLowerCase() || '';
    };

    // 加载 Excel 文件
    const loadExcelFile = async (url: string) => {
        try {
            setIsLoading(true);
            
            // 动态导入 XLSX
            const XLSX = await import('xlsx');
            
            const response = await fetch(url);
            const arrayBuffer = await response.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            
            const sheets = workbook.SheetNames;
            setSheetNames(sheets);
            
            if (sheets.length > 0) {
                const firstSheet = sheets[0];
                setSelectedSheet(firstSheet);
                loadSheet(workbook, firstSheet);
            }
            
            setIsLoading(false);
        } catch (error) {
            console.error('Failed to load Excel file:', error);
            setLoadError('Excel 文件加载失败');
            setIsLoading(false);
        }
    };

    // 加载指定的工作表
    const loadSheet = async (workbook: any, sheetName: string) => {
        // 动态导入 XLSX
        const XLSX = await import('xlsx');
        
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];
        
        if (jsonData.length === 0) {
            setExcelData({ columns: [], rows: [] });
            return;
        }
        
        // 第一行作为列名
        const headers = jsonData[0] || [];
        const columns = headers.map((header, index) => ({
            key: `col_${index}`,
            name: header?.toString() || `Column ${index + 1}`,
            resizable: true,
            sortable: true,
        }));
        
        // 剩余行作为数据
        const rows = jsonData.slice(1).map((row, rowIndex) => {
            const rowData: any = { id: rowIndex };
            headers.forEach((_, colIndex) => {
                rowData[`col_${colIndex}`] = row[colIndex]?.toString() || '';
            });
            return rowData;
        });
        
        setExcelData({ columns, rows });
    };

    // 切换工作表
    const handleSheetChange = async (sheetName: string) => {
        setSelectedSheet(sheetName);
        setIsLoading(true);
        
        try {
            // 动态导入 XLSX
            const XLSX = await import('xlsx');
            
            const response = await fetch(getFullUrl(file.file_url));
            const arrayBuffer = await response.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            await loadSheet(workbook, sheetName);
            setIsLoading(false);
        } catch (error) {
            console.error('Failed to load sheet:', error);
            setLoadError('工作表加载失败');
            setIsLoading(false);
        }
    };

    const getFileIcon = (filename: string) => {
        const ext = getFileExtension(filename);
        switch (ext) {
            case 'html':
            case 'htm':
                return <FileCode className="w-4 h-4" />;
            case 'pdf':
                return <FileText className="w-4 h-4" />;
            case 'png':
            case 'jpg':
            case 'jpeg':
            case 'gif':
            case 'webp':
            case 'svg':
                return <Image className="w-4 h-4" />;
            case 'xlsx':
            case 'xls':
            case 'csv':
                return <FileSpreadsheet className="w-4 h-4" />;
            case 'txt':
            case 'md':
            case 'json':
                return <FileText className="w-4 h-4" />;
            default:
                return <File className="w-4 h-4" />;
        }
    };

    const handleRefresh = () => {
        setIframeKey(prev => prev + 1);
        setIsLoading(true);
        setLoadError(null);
    };

    const handleIframeLoad = () => {
        setIsLoading(false);
        setLoadError(null);
    };

    const handleIframeError = () => {
        setIsLoading(false);
        setLoadError('加载失败，请尝试在新窗口打开');
    };

    // 获取完整的文件URL
    const getFullUrl = (url: string) => {
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        
        // 构造后端文件URL
        // 如果API_BASE包含localhost，且当前访问不是localhost，则替换为当前host
        let baseUrl = API_BASE;
        if (baseUrl.endsWith('/api')) {
            baseUrl = baseUrl.slice(0, -4);
        } else if (baseUrl.endsWith('/api/')) {
            baseUrl = baseUrl.slice(0, -5);
        }
        
        // 如果在浏览器环境，且API_BASE使用localhost，但当前访问不是localhost
        // 则将localhost替换为当前host，以支持IP访问
        if (typeof window !== 'undefined') {
            const currentHost = window.location.hostname;
            if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
                baseUrl = baseUrl.replace('localhost', currentHost).replace('127.0.0.1', currentHost);
            }
        }
        
        return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
    };

    const fullUrl = getFullUrl(file.file_url);

    const renderPreview = () => {
        const ext = getFileExtension(file.file_name);

        // 如果有加载错误，显示错误信息和备选操作
        if (loadError) {
            return (
                <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 text-gray-500 p-8">
                    <AlertCircle className="w-12 h-12 mb-4 text-amber-500" />
                    <p className="text-sm mb-2">{loadError}</p>
                    <p className="text-xs text-gray-400 mb-4 break-all max-w-md text-center">{fullUrl}</p>
                    <div className="flex gap-2">
                        <button
                            onClick={handleRefresh}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300 transition-colors flex items-center gap-2"
                        >
                            <RefreshCw className="w-4 h-4" />
                            重试
                        </button>
                        <a
                            href={fullUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition-colors flex items-center gap-2"
                        >
                            <ExternalLink className="w-4 h-4" />
                            新窗口打开
                        </a>
                    </div>
                </div>
            );
        }

        switch (ext) {
            case 'xlsx':
            case 'xls':
            case 'csv':
                return (
                    <div className="w-full h-full flex flex-col bg-white">
                        {/* 工作表选择器 */}
                        {sheetNames.length > 1 && (
                            <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 bg-gray-50">
                                <span className="text-sm text-gray-600">工作表:</span>
                                <div className="flex gap-1">
                                    {sheetNames.map((name) => (
                                        <button
                                            key={name}
                                            onClick={() => handleSheetChange(name)}
                                            className={`px-3 py-1 text-sm rounded transition-colors ${
                                                selectedSheet === name
                                                    ? 'bg-orange-500 text-white'
                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                            }`}
                                        >
                                            {name}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {/* 数据表格 */}
                        <div className="flex-1 overflow-auto">
                            {isLoading ? (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-2">
                                        <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                                        <span className="text-sm text-gray-500">加载中...</span>
                                    </div>
                                </div>
                            ) : excelData && excelData.rows.length > 0 ? (
                                <Suspense fallback={
                                    <div className="w-full h-full flex items-center justify-center">
                                        <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                                    </div>
                                }>
                                    <DataGrid
                                        columns={excelData.columns}
                                        rows={excelData.rows}
                                        className="rdg-light"
                                        style={{ height: '100%' }}
                                        rowKeyGetter={(row) => row.id}
                                    />
                                </Suspense>
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-gray-400">
                                    <p className="text-sm">工作表为空</p>
                                </div>
                            )}
                        </div>
                    </div>
                );
            case 'html':
            case 'htm':
                return (
                    <div className="w-full h-full relative bg-white">
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                                <div className="flex flex-col items-center gap-2">
                                    <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                                    <span className="text-sm text-gray-500">加载中...</span>
                                </div>
                            </div>
                        )}
                        <iframe
                            key={iframeKey}
                            src={fullUrl}
                            className="w-full h-full border-0"
                            onLoad={handleIframeLoad}
                            onError={handleIframeError}
                            title={file.file_name}
                            style={{ backgroundColor: 'white' }}
                        />
                    </div>
                );
            case 'pdf':
                return (
                    <div className="w-full h-full relative">
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
                                <div className="flex flex-col items-center gap-2">
                                    <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                                    <span className="text-sm text-gray-500">加载 PDF...</span>
                                </div>
                            </div>
                        )}
                        <iframe
                            key={iframeKey}
                            src={fullUrl}
                            className="w-full h-full border-0"
                            onLoad={handleIframeLoad}
                            onError={handleIframeError}
                            title={file.file_name}
                        />
                    </div>
                );
            case 'png':
            case 'jpg':
            case 'jpeg':
            case 'gif':
            case 'webp':
            case 'svg':
                return (
                    <div className="w-full h-full flex items-center justify-center bg-gray-100 p-4 overflow-auto">
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
                                <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                            </div>
                        )}
                        <img
                            src={fullUrl}
                            alt={file.file_name}
                            className="max-w-full max-h-full object-contain"
                            onLoad={() => setIsLoading(false)}
                            onError={() => {
                                setIsLoading(false);
                                setLoadError('图片加载失败');
                            }}
                        />
                    </div>
                );
            case 'txt':
            case 'md':
                return (
                    <div className="w-full h-full relative">
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                                <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                            </div>
                        )}
                        <iframe
                            key={iframeKey}
                            src={fullUrl}
                            className="w-full h-full border-0 bg-white"
                            onLoad={handleIframeLoad}
                            onError={handleIframeError}
                            title={file.file_name}
                        />
                    </div>
                );
            default:
                return (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 text-gray-500">
                        <File className="w-16 h-16 mb-4 text-gray-300" />
                        <p className="text-sm">无法预览此文件类型</p>
                        <p className="text-xs text-gray-400 mt-1">{file.file_name}</p>
                        <a
                            href={fullUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-4 px-4 py-2 bg-gray-700 text-white rounded-lg text-sm hover:bg-gray-800 transition-colors flex items-center gap-2"
                        >
                            <Download className="w-4 h-4" />
                            下载文件
                        </a>
                    </div>
                );
        }
    };

    const HeaderContent = () => (
        <>
            <div className="flex items-center gap-2 min-w-0 flex-1">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-orange-100 text-orange-600 shrink-0">
                    {getFileIcon(file.file_name)}
                </div>
                <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-medium text-gray-800 truncate" title={file.file_name}>
                        {file.file_name}
                    </h3>
                    {file.file_size && (
                        <p className="text-xs text-gray-500">
                            {(file.file_size / 1024).toFixed(1)} KB
                        </p>
                    )}
                </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
                <button
                    onClick={handleRefresh}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="刷新"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
                <a
                    href={fullUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="在新窗口打开"
                >
                    <ExternalLink className="w-4 h-4" />
                </a>
                <a
                    href={fullUrl}
                    download={file.file_name}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="下载"
                >
                    <Download className="w-4 h-4" />
                </a>
                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title={isFullscreen ? "退出全屏" : "全屏"}
                >
                    {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
                <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="关闭"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        </>
    );

    if (isFullscreen) {
        return (
            <div className="fixed inset-0 z-50 bg-white flex flex-col">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 shrink-0">
                    <HeaderContent />
                </div>
                <div className="flex-1 overflow-hidden">
                    {renderPreview()}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white flex flex-col h-full w-full">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 shrink-0">
                <HeaderContent />
            </div>
            <div className="flex-1 overflow-hidden">
                {renderPreview()}
            </div>
        </div>
    );
};

export default FilePreview;
