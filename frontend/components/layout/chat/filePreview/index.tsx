'use client';

import { X, FileText, Image, FileCode, File, ExternalLink, Download, Maximize2, Minimize2, RefreshCw, AlertCircle, FileSpreadsheet } from 'lucide-react';
import { useState, useEffect, lazy, Suspense } from 'react';
import { OutputFile } from '@/types/message';
import { API_BASE } from '@/lib/data';
import MarkDown from '@/components/ui/markDown';

// Dynamically import DataGrid (styles imported in globals.css)
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
    const [markdownContent, setMarkdownContent] = useState<string>('');
    const [selectedSheet, setSelectedSheet] = useState<string>('');
    const [sheetNames, setSheetNames] = useState<string[]>([]);

    useEffect(() => {
        // Reload when file changes
        setIframeKey(prev => prev + 1);
        setIsLoading(true);
        setLoadError(null);
        setExcelData(null);
        setSheetNames([]);
        setSelectedSheet('');

        loadData()
    }, [file?.file_url]);

    if (!file) return null;

    const loadData = () => {
        // If it's an Excel file, load data
        const ext = getFileExtension(file?.file_name || '');
        if (file && (ext === 'xlsx' || ext === 'xls' || ext === 'csv')) {
            loadExcelFile(getFullUrl(file.file_url));
        }else if (file && ext === 'md') { // Markdown file
            loadMarkdownFile(getFullUrl(file.file_url));
        } 
    }

    const getFileExtension = (filename: string): string => {
        return filename.split('.').pop()?.toLowerCase() || '';
    };

    // Load Excel file
    const loadExcelFile = async (url: string) => {
        try {
            setIsLoading(true);

            // Dynamically import XLSX
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
            setLoadError('Failed to load Excel file');
            setIsLoading(false);
        }
    };

    const loadMarkdownFile = async (url: string) => {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Failed to load markdown file');
            }
            const content = await response.text();
            setMarkdownContent(content);
            setIsLoading(false);
        } catch (error) {
            console.error('Error loading markdown file:', error);
            setLoadError('Failed to load Markdown file');
            setIsLoading(false);
        }
    };

    // Helper function to calculate column width
    const calculateColumnWidth = (columnData: string[], headerName: string): number => {
        const MIN_WIDTH = 80;
        const MAX_WIDTH = 400;
        const CHAR_WIDTH = 10; // Average width per character
        const PADDING = 24; // Cell padding

        // Calculate header width
        let maxLength = headerName?.toString().length || 0;

        // Iterate column data to find max length, only check first 100 rows for performance
        const sampleSize = Math.min(columnData.length, 100);
        for (let i = 0; i < sampleSize; i++) {
            const cellValue = columnData[i]?.toString() || '';
            maxLength = Math.max(maxLength, cellValue.length);
        }

        // Calculate width, considering CJK characters take more space
        const calculatedWidth = maxLength * CHAR_WIDTH + PADDING;
        return Math.min(Math.max(calculatedWidth, MIN_WIDTH), MAX_WIDTH);
    };

    // Load specified sheet
    const loadSheet = async (workbook: any, sheetName: string) => {
        // Dynamically import XLSX
        const XLSX = await import('xlsx');

        const worksheet = workbook.Sheets[sheetName];
        // raw: false preserves Excel formatted display values (e.g. percentages, dates)
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '', raw: false }) as any[][];

        if (jsonData.length === 0) {
            setExcelData({ columns: [], rows: [] });
            return;
        }

        // Find max column count (some rows may have more columns)
        let maxCols = 0;
        jsonData.forEach(row => {
            if (Array.isArray(row)) {
                maxCols = Math.max(maxCols, row.length);
            }
        });

        // First row as column names
        const headers = jsonData[0] || [];

        // Extract column data for width calculation
        const columnDataArrays: string[][] = [];
        for (let colIndex = 0; colIndex < maxCols; colIndex++) {
            const colData: string[] = [];
            for (let rowIndex = 1; rowIndex < jsonData.length; rowIndex++) {
                const row = jsonData[rowIndex];
                colData.push(row[colIndex]?.toString() || '');
            }
            columnDataArrays.push(colData);
        }

        // Create column config with auto-calculated width
        const columns = [];
        for (let index = 0; index < maxCols; index++) {
            const headerName = headers[index]?.toString() || `Column ${index + 1}`;
            const columnData = columnDataArrays[index] || [];
            const width = calculateColumnWidth(columnData, headerName);

            columns.push({
                key: `col_${index}`,
                name: headerName,
                resizable: true,
                sortable: true,
                width: width,
                minWidth: 60,
            });
        }

        // Remaining rows as data
        const rows = jsonData.slice(1).map((row, rowIndex) => {
            const rowData: any = { id: rowIndex };
            for (let colIndex = 0; colIndex < maxCols; colIndex++) {
                rowData[`col_${colIndex}`] = row[colIndex]?.toString() || '';
            }
            return rowData;
        });
        setExcelData({ columns, rows });
    };

    // Switch sheet
    const handleSheetChange = async (sheetName: string) => {
        setSelectedSheet(sheetName);
        setIsLoading(true);

        try {
            // Dynamically import XLSX
            const XLSX = await import('xlsx');

            const response = await fetch(getFullUrl(file.file_url));
            const arrayBuffer = await response.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            await loadSheet(workbook, sheetName);
            setIsLoading(false);
        } catch (error) {
            console.error('Failed to load sheet:', error);
            setLoadError('Failed to load sheet');
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
        loadData()
    };

    const handleIframeLoad = () => {
        setIsLoading(false);
        setLoadError(null);
    };

    const handleIframeError = () => {
        setIsLoading(false);
        setLoadError('Failed to load, please try opening in a new window');
    };

    // Get full file URL
    const getFullUrl = (url: string) => {
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }

        // Construct backend file URL
        // If API_BASE contains localhost but current access is not localhost, replace with current host
        let baseUrl = API_BASE;
        if (baseUrl.endsWith('/api')) {
            baseUrl = baseUrl.slice(0, -4);
        } else if (baseUrl.endsWith('/api/')) {
            baseUrl = baseUrl.slice(0, -5);
        }

        // In browser environment, if API_BASE uses localhost but current access is not localhost
        // Replace localhost with current host to support IP access
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

        // If there's a load error, show error message and fallback actions
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
                            Retry
                        </button>
                        <a
                            href={fullUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition-colors flex items-center gap-2"
                        >
                            <ExternalLink className="w-4 h-4" />
                            Open in New Window
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
                        {/* Sheet selector */}
                        {sheetNames.length > 1 && (
                            <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 bg-gray-50">
                                <span className="text-sm text-gray-600">Sheet:</span>
                                <div className="flex gap-1">
                                    {sheetNames.map((name) => (
                                        <button
                                            key={name}
                                            onClick={() => handleSheetChange(name)}
                                            className={`px-3 py-1 text-sm rounded transition-colors ${selectedSheet === name
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

                        {/* Data table */}
                        <div className="flex-1 overflow-auto">
                            {isLoading ? (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-2">
                                        <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                                        <span className="text-sm text-gray-500">Loading...</span>
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
                                    <p className="text-sm">Sheet is empty</p>
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
                                    <span className="text-sm text-gray-500">Loading...</span>
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
                                    <span className="text-sm text-gray-500">Loading PDF...</span>
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
                                setLoadError('Failed to load image');
                            }}
                        />
                    </div>
                );
            case 'txt':
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
            case 'md':
                return (
                    <div className="w-full h-full relative">
                        {isLoading ? (
                            <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                                <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
                            </div>
                        ) : loadError ? (
                            <div className="w-full h-full flex flex-col items-center justify-center p-4">
                                <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
                                <p className="text-sm text-gray-600 mb-2">{loadError}</p>
                                <a
                                    href={fullUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-3 py-1.5 bg-orange-500 text-white rounded text-sm hover:bg-orange-600 transition-colors flex items-center gap-1"
                                >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                    Open in New Window
                                </a>
                            </div>
                        ) : (
                            <div className="w-full h-full p-4 overflow-auto">
                                <MarkDown content={markdownContent || ''} />
                            </div>
                        )}
                    </div>
                )
            default:
                return (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 text-gray-500">
                        <File className="w-16 h-16 mb-4 text-gray-300" />
                        <p className="text-sm">Cannot preview this file type</p>
                        <p className="text-xs text-gray-400 mt-1">{file.file_name}</p>
                        <a
                            href={fullUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-4 px-4 py-2 bg-gray-700 text-white rounded-lg text-sm hover:bg-gray-800 transition-colors flex items-center gap-2"
                        >
                            <Download className="w-4 h-4" />
                            Download File
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
                    title="Refresh"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
                <a
                    href={fullUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="Open in New Window"
                >
                    <ExternalLink className="w-4 h-4" />
                </a>
                <a
                    href={fullUrl}
                    download={file.file_name}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="Download"
                >
                    <Download className="w-4 h-4" />
                </a>
                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
                >
                    {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
                <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-200 rounded-lg transition-colors text-gray-600"
                    title="Close"
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
