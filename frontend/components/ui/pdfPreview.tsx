'use client';

import { useState, useEffect } from 'react';
import { X, Download, FileText, Loader2, ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from 'lucide-react';

interface IProps {
  url: string;
  onClose?: () => void;
}

const PdfPreview: React.FC<IProps> = ({ url, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    // 预加载 PDF
    const checkPdf = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(url, { method: 'HEAD' });
        if (!response.ok) throw new Error('无法访问 PDF 文件');
        setLoading(false);
      } catch (err) {
        console.error('Error loading PDF:', err);
        setError('无法加载 PDF 文件');
        setLoading(false);
      }
    };
    checkPdf();
  }, [url]);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = url.split('/').pop() || 'document.pdf';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 200));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 50));
  };

  const handleResetZoom = () => {
    setZoom(100);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-red-500" />
            <h3 className="text-lg font-semibold">加载失败</h3>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
            >
              下载文件
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
              >
                关闭
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-gray-700" />
            <h3 className="font-semibold text-lg">PDF 预览</h3>
          </div>
          
          {/* Toolbar */}
          <div className="flex items-center gap-2">
            {/* Zoom Controls */}
            <div className="flex items-center gap-1 border rounded-lg px-2 py-1">
              <button
                onClick={handleZoomOut}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="缩小"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleResetZoom}
                className="px-2 py-1 text-sm hover:bg-gray-100 rounded transition-colors min-w-[60px]"
                title="重置缩放"
              >
                {zoom}%
              </button>
              <button
                onClick={handleZoomIn}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="放大"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="下载"
            >
              <Download className="w-5 h-5" />
            </button>

            {/* Close Button */}
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="关闭"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* PDF Viewer */}
        <div className="flex-1 overflow-auto bg-gray-100 p-4">
          <div 
            className="mx-auto bg-white shadow-lg"
            style={{ 
              width: `${zoom}%`,
              maxWidth: '100%',
              minHeight: '100%'
            }}
          >
            <iframe
              src={url}
              className="w-full h-full"
              style={{ 
                minHeight: '600px',
                border: 'none'
              }}
              title="PDF Preview"
            />
          </div>
        </div>

        {/* Footer Info */}
        <div className="px-4 py-2 border-t bg-gray-50 text-sm text-gray-600">
          <div className="flex items-center justify-between">
            <span>使用浏览器内置 PDF 阅读器</span>
            <span className="text-xs text-gray-500">
              提示: 可以使用浏览器的 PDF 工具栏进行更多操作
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PdfPreview;

