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

import { useState, useEffect } from 'react';
import { X, Download, Presentation, Loader2, ChevronLeft, ChevronRight, Maximize2, Minimize2, Info } from 'lucide-react';
import { API_BASE } from '@/lib/data';

// --- Image mode: single stitched image ---
interface ImageModeData {
  mode: 'image';
  total_slides: number;
  image: string;
}

// --- Text mode types (fallback) ---
interface SlideText {
  text: string;
  fontSize: number | null;
  bold: boolean;
  italic: boolean;
  color: string | null;
  left: number;
  top: number;
  width: number;
  tableData?: string[][];
}

interface SlideImage {
  data: string;
  left: number;
  top: number;
  width: number;
  height: number;
}

interface TextSlide {
  number: number;
  texts: SlideText[];
  images: SlideImage[];
  notes: string;
  background_color: string | null;
}

interface TextModeData {
  mode: 'text';
  total_slides: number;
  slide_width: number;
  slide_height: number;
  slides: TextSlide[];
  notice?: string;
}

type PptxData = ImageModeData | TextModeData;

interface IProps {
  url: string;
  onClose?: () => void;
}

const PptxPreview: React.FC<IProps> = ({ url, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pptxData, setPptxData] = useState<PptxData | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    loadPptx();
  }, [url]);

  const getApiBase = () => {
    let baseUrl = API_BASE;
    if (baseUrl.endsWith('/api')) baseUrl = baseUrl.slice(0, -4);
    else if (baseUrl.endsWith('/api/')) baseUrl = baseUrl.slice(0, -5);
    if (typeof window !== 'undefined') {
      const currentHost = window.location.hostname;
      if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
        baseUrl = baseUrl.replace('localhost', currentHost).replace('127.0.0.1', currentHost);
      }
    }
    return baseUrl;
  };

  const getUrlPath = (fileUrl: string): string => {
    try {
      if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) return new URL(fileUrl).pathname;
      return fileUrl;
    } catch { return fileUrl; }
  };

  const loadPptx = async () => {
    try {
      setLoading(true);
      setError(null);
      const baseUrl = getApiBase();
      const filePath = getUrlPath(url);
      const apiUrl = `${baseUrl}/api/files/pptx-preview?path=${encodeURIComponent(filePath)}`;
      const response = await fetch(apiUrl);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to load PPTX');
      }
      const data: PptxData = await response.json();
      setPptxData(data);
      setCurrentSlide(0);
      setLoading(false);
    } catch (err) {
      console.error('Error loading PPTX:', err);
      setError('无法加载 PPTX 文件');
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = url.split('/').pop() || 'presentation.pptx';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // --- Text mode: render a single slide ---
  const renderTextSlide = (slide: TextSlide) => {
    const data = pptxData as TextModeData;
    const aspectRatio = data.slide_height / data.slide_width;
    return (
      <div
        className="relative bg-white shadow-lg mx-auto"
        style={{
          width: '100%', maxWidth: '900px',
          aspectRatio: `${1 / aspectRatio}`, overflow: 'hidden',
          backgroundColor: slide.background_color || 'white',
        }}
      >
        {slide.images.map((img, idx) => (
          <div key={`img-${idx}`} className="absolute" style={{ left: `${img.left}%`, top: `${img.top}%`, width: `${img.width}%`, height: `${img.height}%` }}>
            <img src={img.data} alt={`Slide image ${idx + 1}`} className="w-full h-full object-contain" />
          </div>
        ))}
        {slide.texts.map((textItem, idx) => {
          if (textItem.tableData) {
            return (
              <div key={`text-${idx}`} className="absolute px-2" style={{ left: `${textItem.left}%`, top: `${textItem.top}%`, width: `${textItem.width}%` }}>
                <table className="w-full border-collapse text-xs"><tbody>
                  {textItem.tableData.map((row, ri) => (
                    <tr key={ri}>{row.map((cell, ci) => <td key={ci} className="border border-gray-300 px-2 py-1">{cell}</td>)}</tr>
                  ))}
                </tbody></table>
              </div>
            );
          }
          const fs = Math.max(8, Math.min((textItem.fontSize || 14) * 0.6, 36));
          return (
            <div key={`text-${idx}`} className="absolute px-2" style={{
              left: `${textItem.left}%`, top: `${textItem.top}%`, width: `${textItem.width}%`,
              fontSize: `${fs}px`, fontWeight: textItem.bold ? 'bold' : 'normal',
              fontStyle: textItem.italic ? 'italic' : 'normal', color: textItem.color || '#333333',
              lineHeight: 1.3, wordBreak: 'break-word',
            }}>
              {textItem.text}
            </div>
          );
        })}
        {slide.texts.length === 0 && slide.images.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400"><span className="text-sm">（空白幻灯片）</span></div>
        )}
      </div>
    );
  };

  // --- Loading / Error states ---
  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            <span className="text-sm text-gray-600">正在解析演示文稿...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <div className="flex items-center gap-3 mb-4">
            <Presentation className="w-6 h-6 text-red-500" />
            <h3 className="text-lg font-semibold">加载失败</h3>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="flex gap-2">
            <button onClick={handleDownload} className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800">下载文件</button>
            {onClose && <button onClick={onClose} className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50">关闭</button>}
          </div>
        </div>
      </div>
    );
  }

  if (!pptxData) return null;

  const containerClass = isFullscreen
    ? 'fixed inset-0 bg-black/90 flex flex-col z-50'
    : 'fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4';
  const contentClass = isFullscreen
    ? 'bg-white flex flex-col w-full h-full'
    : 'bg-white rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col';

  // ========== Image mode: single stitched image ==========
  if (pptxData.mode === 'image') {
    const data = pptxData as ImageModeData;
    return (
      <div className={containerClass}>
        <div className={contentClass}>
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b shrink-0">
            <div className="flex items-center gap-3">
              <Presentation className="w-5 h-5 text-orange-600" />
              <h3 className="font-semibold text-lg">演示文稿预览</h3>
              <span className="text-sm text-gray-500">{data.total_slides} 张幻灯片</span>
              <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">高保真</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setIsFullscreen(!isFullscreen)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title={isFullscreen ? '退出全屏' : '全屏'}>
                {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
              </button>
              <button onClick={handleDownload} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="下载">
                <Download className="w-5 h-5" />
              </button>
              {onClose && (
                <button onClick={onClose} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="关闭">
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
          {/* Single scrollable image */}
          <div className="flex-1 overflow-auto bg-gray-200 p-4">
            <img
              src={data.image}
              alt={`全部 ${data.total_slides} 张幻灯片`}
              className="w-full max-w-[900px] mx-auto h-auto rounded shadow-lg"
              style={{ display: 'block' }}
            />
          </div>
        </div>
      </div>
    );
  }

  // ========== Text mode fallback: per-slide navigation ==========
  const textData = pptxData as TextModeData;
  const slide = textData.slides[currentSlide];

  return (
    <div className={containerClass}>
      <div className={contentClass}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="flex items-center gap-3">
            <Presentation className="w-5 h-5 text-orange-600" />
            <h3 className="font-semibold text-lg">演示文稿预览</h3>
            <span className="text-sm text-gray-500">{textData.total_slides} 张幻灯片</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Slide navigation */}
            <div className="flex items-center gap-1 border rounded-lg px-2 py-1">
              <button onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))} disabled={currentSlide === 0} className="p-1 hover:bg-gray-100 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed" title="上一页">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 py-1 text-sm min-w-[80px] text-center">{currentSlide + 1} / {textData.total_slides}</span>
              <button onClick={() => setCurrentSlide(prev => Math.min(textData.total_slides - 1, prev + 1))} disabled={currentSlide === textData.total_slides - 1} className="p-1 hover:bg-gray-100 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed" title="下一页">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <button onClick={() => setIsFullscreen(!isFullscreen)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title={isFullscreen ? '退出全屏' : '全屏'}>
              {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
            </button>
            <button onClick={handleDownload} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="下载">
              <Download className="w-5 h-5" />
            </button>
            {onClose && (
              <button onClick={onClose} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="关闭">
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Text mode notice */}
        {textData.notice && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border-b border-amber-200 text-xs text-amber-700 shrink-0">
            <Info className="w-3.5 h-3.5 shrink-0" />
            <span>简化预览模式 — 重新生成 PPTX 可获得高保真渲染</span>
          </div>
        )}

        {/* Slide content */}
        <div className="flex-1 overflow-auto bg-gray-200 p-6 flex items-center justify-center">
          {slide && renderTextSlide(slide)}
        </div>

        {/* Notes */}
        {slide?.notes && (
          <div className="px-4 py-2 border-t bg-gray-50 text-sm text-gray-600 max-h-24 overflow-auto shrink-0">
            <span className="font-medium text-gray-700">备注：</span><span>{slide.notes}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PptxPreview;
