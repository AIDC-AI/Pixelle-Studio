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
import * as XLSX from 'xlsx';
import { X, Download, FileSpreadsheet, Loader2 } from 'lucide-react';

interface IProps {
  url: string;
  onClose?: () => void;
}

interface SheetData {
  name: string;
  data: any[][];
  headers: string[];
}

const ExcelPreview: React.FC<IProps> = (props) => {
  const { url, onClose } = props
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadExcelFile();
  }, [url]);

  const loadExcelFile = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch file
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch file');

      const arrayBuffer = await response.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer, { type: 'array' });

      // Parse all worksheets
      const parsedSheets: SheetData[] = workbook.SheetNames.map((sheetName) => {
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];

        // Extract headers and data
        const headers = jsonData[0]?.map((h: any) => String(h || '')) || [];
        const data = jsonData.slice(1);

        return {
          name: sheetName,
          headers,
          data,
        };
      });

      setSheets(parsedSheets);
    } catch (err) {
      console.error('Error loading Excel file:', err);
      setError('Unable to load Excel file');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = url.split('/').pop() || 'file.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
            <FileSpreadsheet className="w-6 h-6 text-red-500" />
            <h3 className="text-lg font-semibold">Loading Failed</h3>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
            >
              Download File
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const currentSheet = sheets[activeSheet];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-5 h-5 text-gray-700" />
            <h3 className="font-semibold text-lg">Excel Preview</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Download"
            >
              <Download className="w-5 h-5" />
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="Close"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Sheet Tabs */}
        {sheets.length > 1 && (
          <div className="flex gap-1 px-4 pt-2 border-b overflow-x-auto">
            {sheets.map((sheet, index) => (
              <button
                key={index}
                onClick={() => setActiveSheet(index)}
                className={`px-4 py-2 rounded-t-lg transition-colors ${
                  activeSheet === index
                    ? 'bg-gray-100 font-medium'
                    : 'hover:bg-gray-50'
                }`}
              >
                {sheet.name}
              </button>
            ))}
          </div>
        )}

        {/* Table Content */}
        <div className="flex-1 overflow-auto p-4 text-gray-600">
          {currentSheet && (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    {currentSheet.headers.map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-2 text-left font-medium text-gray-700 border-b border-r last:border-r-0"
                      >
                        {header || `Column ${index + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {currentSheet.data.map((row, rowIndex) => (
                    <tr key={rowIndex} className="hover:bg-gray-50 border-b last:border-b-0">
                      {currentSheet.headers.map((_, colIndex) => (
                        <td
                          key={colIndex}
                          className="px-4 py-2 border-r last:border-r-0"
                        >
                          {row[colIndex] !== undefined && row[colIndex] !== null
                            ? String(row[colIndex])
                            : ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="px-4 py-2 border-t bg-gray-50 text-sm text-gray-600">
          Total {currentSheet?.data.length || 0} rows × {currentSheet?.headers.length || 0} columns
        </div>
      </div>
    </div>
  );
}

export default ExcelPreview