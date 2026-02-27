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

import { useState, useEffect, useRef, useCallback } from 'react';
import { RefreshCw, AlertCircle, ExternalLink } from 'lucide-react';

interface IProps {
  url: string;
}

const DocxPreviewInline: React.FC<IProps> = ({ url }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [retryCount, setRetryCount] = useState(0);

  const loadDocx = useCallback(async () => {
    // Wait for containerRef to be available
    if (!containerRef.current) {
      // Retry after a short delay if ref isn't ready yet
      setTimeout(() => {
        if (containerRef.current) {
          loadDocx();
        }
      }, 100);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(url);
      if (!response.ok) throw new Error(`Failed to fetch DOCX file (${response.status})`);

      const arrayBuffer = await response.arrayBuffer();

      // Dynamically import docx-preview
      const { renderAsync } = await import('docx-preview');

      if (containerRef.current) {
        containerRef.current.innerHTML = '';

        await renderAsync(arrayBuffer, containerRef.current, undefined, {
          className: 'docx-preview-wrapper',
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          experimental: false,
          trimXmlDeclaration: true,
          useBase64URL: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
        });
      }

      setLoading(false);
    } catch (err) {
      console.error('Error loading DOCX:', err);
      setError(`无法加载 DOCX 文件: ${err instanceof Error ? err.message : String(err)}`);
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    // Use requestAnimationFrame to ensure the DOM is ready
    const raf = requestAnimationFrame(() => {
      loadDocx();
    });
    return () => cancelAnimationFrame(raf);
  }, [url, retryCount, loadDocx]);

  const handleRefresh = () => {
    setRetryCount(prev => prev + 1);
  };

  return (
    <div className="w-full h-full overflow-auto bg-gray-100 relative">
      {/* Loading overlay - always on top */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
          <div className="flex flex-col items-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-orange-500" />
            <span className="text-sm text-gray-500">正在加载文档...</span>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && !loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-4 bg-white z-10">
          <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
          <p className="text-sm text-gray-600 mb-2">{error}</p>
          <div className="flex gap-2">
            <button
              onClick={handleRefresh}
              className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              重试
            </button>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-orange-500 text-white rounded text-sm hover:bg-orange-600 transition-colors flex items-center gap-1"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              在新窗口中打开
            </a>
          </div>
        </div>
      )}

      {/* Container div - ALWAYS in DOM so containerRef is never null */}
      <div ref={containerRef} className="docx-preview-container p-4" />
    </div>
  );
};

export default DocxPreviewInline;
