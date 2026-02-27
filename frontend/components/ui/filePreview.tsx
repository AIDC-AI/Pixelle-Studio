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

import { useState } from 'react';
import { FileSpreadsheet, FileText, Image as ImageIcon, File, Presentation } from 'lucide-react';
import ExcelPreview from './excelPreview';
import PdfPreview from './pdfPreview';
import DocxPreview from './docxPreview';
import PptxPreview from './pptxPreview';

interface FilePreviewProps {
  url: string;
  filename?: string;
}

export default function FilePreview({ url, filename }: FilePreviewProps) {
  const [showPreview, setShowPreview] = useState(false);
  const [previewType, setPreviewType] = useState<'excel' | 'pdf' | 'docx' | 'pptx' | null>(null);

  // Get file extension
  const getFileExtension = (url: string) => {
    const urlWithoutQuery = url.split('?')[0];
    const parts = urlWithoutQuery.split('.');
    return parts[parts.length - 1]?.toLowerCase() || '';
  };

  const extension = getFileExtension(url);
  const displayName = filename || url.split('/').pop() || 'file';

  // Determine file type
  const isExcel = ['xlsx', 'xls', 'xlsm', 'xlsb'].includes(extension);
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(extension);
  const isPdf = extension === 'pdf';
  const isText = ['txt', 'md', 'json', 'csv'].includes(extension);
  const isDocx = ['docx'].includes(extension);
  const isPptx = ['pptx'].includes(extension);

  // Get icon
  const getIcon = () => {
    if (isExcel) return <FileSpreadsheet className="w-5 h-5" />;
    if (isImage) return <ImageIcon className="w-5 h-5" />;
    if (isPptx) return <Presentation className="w-5 h-5" />;
    if (isDocx) return <FileText className="w-5 h-5" />;
    if (isPdf || isText) return <FileText className="w-5 h-5" />;
    return <File className="w-5 h-5" />;
  };

  // Get color
  const getColor = () => {
    if (isExcel) return 'text-green-600 bg-green-50 border-green-200';
    if (isImage) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (isPdf) return 'text-red-600 bg-red-50 border-red-200';
    if (isPptx) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (isDocx) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (isText) return 'text-gray-600 bg-gray-50 border-gray-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const handleClick = () => {
    if (isExcel) {
      setPreviewType('excel');
      setShowPreview(true);
    } else if (isPdf) {
      setPreviewType('pdf');
      setShowPreview(true);
    } else if (isDocx) {
      setPreviewType('docx');
      setShowPreview(true);
    } else if (isPptx) {
      setPreviewType('pptx');
      setShowPreview(true);
    } else if (isImage) {
      window.open(url, '_blank');
    } else {
      // Download other file types
      const link = document.createElement('a');
      link.href = url;
      link.download = displayName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleClosePreview = () => {
    setShowPreview(false);
    setPreviewType(null);
  };

  return (
    <>
      <button
        onClick={handleClick}
        className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border transition-all hover:shadow-md ${getColor()}`}
      >
        {getIcon()}
        <span className="text-sm font-medium">{displayName}</span>
        <span className="text-xs opacity-60 uppercase">{extension}</span>
      </button>

      {showPreview && previewType === 'excel' && (
        <ExcelPreview url={url} onClose={handleClosePreview} />
      )}

      {showPreview && previewType === 'pdf' && (
        <PdfPreview url={url} onClose={handleClosePreview} />
      )}

      {showPreview && previewType === 'docx' && (
        <DocxPreview url={url} onClose={handleClosePreview} />
      )}

      {showPreview && previewType === 'pptx' && (
        <PptxPreview url={url} onClose={handleClosePreview} />
      )}
    </>
  );
}
