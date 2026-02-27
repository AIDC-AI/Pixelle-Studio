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
import { RefreshCw, AlertCircle, ExternalLink, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { API_BASE } from '@/lib/data';

// --- Image mode: single stitched image of all slides ---
interface ImageModeData {
  mode: 'image';
  total_slides: number;
  image: string; // single base64 data URL (all slides stitched vertically)
}

// --- Text mode types (python-pptx fallback, per-slide navigation) ---
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
}

const PptxPreviewInline: React.FC<IProps> = ({ url }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pptxData, setPptxData] = useState<PptxData | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0); // only used in text mode

  useEffect(() => {
    loadPptx();
  }, [url]);

  const getApiBase = () => {
    let baseUrl = API_BASE;
    if (baseUrl.endsWith('/api')) {
      baseUrl = baseUrl.slice(0, -4);
    } else if (baseUrl.endsWith('/api/')) {
      baseUrl = baseUrl.slice(0, -5);
    }
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
      if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) {
        const urlObj = new URL(fileUrl);
        return urlObj.pathname;
      }
      return fileUrl;
    } catch {
      return fileUrl;
    }
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
      const errMsg = err instanceof Error ? err.message : String(err);
      setError(`无法加载 PPTX 文件: ${errMsg}`);
      setLoading(false);
    }
  };

  // --- Text mode: per-slide rendering (fallback) ---
  const renderTextSlide = (slide: TextSlide) => {
    const data = pptxData as TextModeData;
    const aspectRatio = data.slide_height / data.slide_width;
    return (
      <div
        className="relative bg-white shadow-lg mx-auto"
        style={{
          width: '100%',
          maxWidth: '800px',
          aspectRatio: `${1 / aspectRatio}`,
          overflow: 'hidden',
          backgroundColor: slide.background_color || 'white',
        }}
      >
        {slide.images.map((img, idx) => (
          <div
            key={`img-${idx}`}
            className="absolute"
            style={{ left: `${img.left}%`, top: `${img.top}%`, width: `${img.width}%`, height: `${img.height}%` }}
          >
            <img src={img.data} alt={`Slide image ${idx + 1}`} className="w-full h-full object-contain" />
          </div>
        ))}
        {slide.texts.map((textItem, idx) => {
          if (textItem.tableData) {
            return (
              <div key={`text-${idx}`} className="absolute px-2" style={{ left: `${textItem.left}%`, top: `${textItem.top}%`, width: `${textItem.width}%` }}>
                <table className="w-full border-collapse text-xs">
                  <tbody>
                    {textItem.tableData.map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        {row.map((cell, cellIdx) => (
                          <td key={cellIdx} className="border border-gray-300 px-2 py-1">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
          const baseFontSize = textItem.fontSize || 14;
          const responsiveFontSize = Math.max(8, Math.min(baseFontSize * 0.5, 32));
          return (
            <div
              key={`text-${idx}`}
              className="absolute px-2"
              style={{
                left: `${textItem.left}%`, top: `${textItem.top}%`, width: `${textItem.width}%`,
                fontSize: `${responsiveFontSize}px`, fontWeight: textItem.bold ? 'bold' : 'normal',
                fontStyle: textItem.italic ? 'italic' : 'normal', color: textItem.color || '#333333',
                lineHeight: 1.3, wordBreak: 'break-word',
              }}
            >
              {textItem.text}
            </div>
          );
        })}
        {slide.texts.length === 0 && slide.images.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            <span className="text-sm">（空白幻灯片）</span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-2">
          <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
          <span className="text-sm text-gray-500">正在解析演示文稿...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-4">
        <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
        <p className="text-sm text-gray-600 mb-2">{error}</p>
        <div className="flex gap-2">
          <button
            onClick={() => loadPptx()}
            className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            重试
          </button>
          <a
            href={url} target="_blank" rel="noopener noreferrer"
            className="px-3 py-1.5 bg-orange-500 text-white rounded text-sm hover:bg-orange-600 transition-colors flex items-center gap-1"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            下载文件
          </a>
        </div>
      </div>
    );
  }

  if (!pptxData) return null;

  // ========== Image mode: single stitched long image ==========
  if (pptxData.mode === 'image') {
    const data = pptxData as ImageModeData;
    return (
      <div className="w-full h-full flex flex-col bg-white">
        {/* Header */}
        <div className="flex items-center justify-center gap-2 px-4 py-2 border-b bg-gray-50 text-sm text-gray-600">
          <span>{data.total_slides} 张幻灯片</span>
        </div>
        {/* Scrollable image */}
        <div className="flex-1 overflow-auto bg-gray-200 p-3">
          <img
            src={data.image}
            alt={`全部 ${data.total_slides} 张幻灯片`}
            className="w-full h-auto rounded shadow-sm"
            style={{ display: 'block' }}
          />
        </div>
      </div>
    );
  }

  // ========== Text mode fallback: per-slide navigation ==========
  const textData = pptxData as TextModeData;
  const slide = textData.slides[currentSlide];

  return (
    <div className="w-full h-full flex flex-col bg-white">
      {/* Notice */}
      {textData.notice && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border-b border-amber-200 text-xs text-amber-700">
          <Info className="w-3.5 h-3.5 shrink-0" />
          <span>简化预览模式 — 重新生成 PPTX 可获得高保真渲染</span>
        </div>
      )}
      {/* Navigation */}
      <div className="flex items-center justify-center gap-3 px-4 py-2 border-b bg-gray-50">
        <button
          onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
          disabled={currentSlide === 0}
          className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm text-gray-600">
          {currentSlide + 1} / {textData.total_slides}
        </span>
        <button
          onClick={() => setCurrentSlide(prev => Math.min(textData.total_slides - 1, prev + 1))}
          disabled={currentSlide === textData.total_slides - 1}
          className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
      {/* Slide content */}
      <div className="flex-1 overflow-auto bg-gray-200 p-4 flex items-center justify-center">
        {slide && renderTextSlide(slide)}
      </div>
      {/* Notes */}
      {slide?.notes && (
        <div className="px-4 py-2 border-t bg-gray-50 text-xs text-gray-600 max-h-16 overflow-auto">
          <span className="font-medium">备注：</span>{slide.notes}
        </div>
      )}
    </div>
  );
};

export default PptxPreviewInline;
