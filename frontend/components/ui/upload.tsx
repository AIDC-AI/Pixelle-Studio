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

import React, { useRef, useState } from 'react';

export interface UploadFile {
  uid: string;
  name: string;
  status?: 'uploading' | 'done' | 'error' | 'removed';
  url?: string;
  thumbUrl?: string;
  size?: number;
  type?: string;
  originFileObj?: File;
  percent?: number;
  error?: any;
  response?: any;
}

export const LIST_IGNORE = "Cannot upload more files!"

interface UploadProps {
  accept?: string;
  multiple?: boolean;
  maxCount?: number;
  maxSize?: number; // in bytes
  fileList?: UploadFile[];
  defaultFileList?: UploadFile[];
  disabled?: boolean;
  listType?: 'text' | 'picture' | 'picture-card';
  showUploadList?: boolean;
  beforeUpload?: (file: File, fileList: File[]) => boolean | Promise<boolean>;
  onChange?: (info: { file: UploadFile; fileList: UploadFile[] }) => void;
  onRemove?: (file: UploadFile) => void | boolean | Promise<void | boolean>;
  customRequest?: (options: {
    file: File;
    onProgress: (percent: number) => void;
    onSuccess: (response: any) => void;
    onError: (error: any) => void;
  }) => void;
  children?: React.ReactNode;
  className?: string;
}

export const Upload: React.FC<UploadProps> = ({
  accept,
  multiple = false,
  maxCount,
  maxSize,
  fileList: controlledFileList,
  defaultFileList = [],
  disabled = false,
  listType = 'text',
  showUploadList = true,
  beforeUpload,
  onChange,
  onRemove,
  customRequest,
  children,
  className = '',
}) => {
  const [internalFileList, setInternalFileList] = useState<UploadFile[]>(defaultFileList);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const fileList = controlledFileList ?? internalFileList;

  const updateFileList = (newFileList: UploadFile[]) => {
    if (controlledFileList === undefined) {
      setInternalFileList(newFileList);
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    await processFiles(files);
    // Reset input value to allow selecting the same file again
    e.target.value = '';
  };

  const processFiles = async (files: File[]) => {
    if (maxCount && fileList.length + files.length > maxCount) {
      files = files.slice(0, maxCount - fileList.length);
    }

    for (const file of files) {
      // Check file size
      if (maxSize && file.size > maxSize) {
        console.error(`File ${file.name} exceeds max size`);
        continue;
      }

      // Before upload hook
      if (beforeUpload) {
        const result = await beforeUpload(file, files);
        if (result === false) continue;
      }

      const uploadFile: UploadFile = {
        uid: `${Date.now()}-${Math.random()}`,
        name: file.name,
        status: 'uploading',
        size: file.size,
        type: file.type,
        originFileObj: file,
        percent: 0,
      };

      const newFileList = [...fileList, uploadFile];
      updateFileList(newFileList);
      onChange?.({ file: uploadFile, fileList: newFileList });

      // Handle upload
      if (customRequest) {
        customRequest({
          file,
          onProgress: (percent) => {
            uploadFile.percent = percent;
            uploadFile.status = 'uploading';
            const updatedList = newFileList.map((f) =>
              f.uid === uploadFile.uid ? { ...uploadFile } : f
            );
            updateFileList(updatedList);
            onChange?.({ file: uploadFile, fileList: updatedList });
          },
          onSuccess: (response) => {
            uploadFile.status = 'done';
            uploadFile.percent = 100;
            uploadFile.url = response?.url;
            // If the server returned a file_name, update to the server-saved filename
            if (response?.file_name) {
              uploadFile.name = response.file_name;
            }
            const updatedList = newFileList.map((f) =>
              f.uid === uploadFile.uid ? { ...uploadFile } : f
            );
            updateFileList(updatedList);
            onChange?.({ file: uploadFile, fileList: updatedList });
          },
          onError: (error) => {
            uploadFile.status = 'error';
            uploadFile.error = error;
            const updatedList = newFileList.map((f) =>
              f.uid === uploadFile.uid ? { ...uploadFile } : f
            );
            updateFileList(updatedList);
            onChange?.({ file: uploadFile, fileList: updatedList });
          },
        });
      } else {
        // Default behavior: just mark as done
        uploadFile.status = 'done';
        uploadFile.percent = 100;
        const updatedList = newFileList.map((f) =>
          f.uid === uploadFile.uid ? { ...uploadFile } : f
        );
        updateFileList(updatedList);
        onChange?.({ file: uploadFile, fileList: updatedList });
      }
    }
  };

  const handleRemove = async (file: UploadFile) => {
    if (onRemove) {
      const result = await onRemove(file);
      if (result === false) return;
    }

    const newFileList = fileList.filter((f) => f.uid !== file.uid);
    updateFileList(newFileList);
    onChange?.({ file: { ...file, status: 'removed' }, fileList: newFileList });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    await processFiles(files);
  };

  const renderFileList = () => {
    if (!showUploadList || fileList.length === 0) return null;

    if (listType === 'picture-card') {
      return (
        <div className="flex flex-wrap gap-2">
          {fileList.map((file) => (
            <div
              key={file.uid}
              className="relative w-24 h-24 border border-gray-200 rounded overflow-hidden group"
            >
              {file.thumbUrl || file.url ? (
                <img
                  src={file.thumbUrl || file.url}
                  alt={file.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                  <FileIcon />
                </div>
              )}
              {file.status === 'uploading' && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                  <div className="text-white text-xs">{file.percent}%</div>
                </div>
              )}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                <button
                  onClick={() => handleRemove(file)}
                  className="text-white hover:text-red-400"
                >
                  <TrashIcon />
                </button>
              </div>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="mt-2 space-y-1">
        {fileList.map((file) => (
          <div
            key={file.uid}
            className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group"
          >
            <FileIcon className="shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate">{file.name}</div>
              {file.status === 'uploading' && (
                <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                  <div
                    className="bg-blue-500 h-1 rounded-full transition-all"
                    style={{ width: `${file.percent}%` }}
                  />
                </div>
              )}
            </div>
            {file.status === 'done' && (
              <CheckIcon className="text-green-500 shrink-0" />
            )}
            {file.status === 'error' && (
              <ErrorIcon className="text-red-500 shrink-0" />
            )}
            <button
              onClick={() => handleRemove(file)}
              className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
            >
              <TrashIcon className="w-4 h-4 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        ))}
      </div>
    );
  };

  const showUploadButton = !maxCount || fileList.length < maxCount;

  if (listType === 'picture-card') {
    return (
      <div className={className}>
        <div className="flex flex-wrap gap-2">
          {renderFileList()}
          {showUploadButton && (
            <div
              onClick={handleClick}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`w-24 h-24 border-2 border-dashed rounded flex flex-col items-center justify-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-blue-400'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {children || (
                <>
                  <UploadIcon className="w-6 h-6 text-gray-400 mb-1" />
                  <div className="text-xs text-gray-500">Upload</div>
                </>
              )}
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileChange}
          className="hidden"
          disabled={disabled}
        />
      </div>
    );
  }

  return (
    <div className={className}>
      {showUploadButton && (
        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`inline-block ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {children || (
            <button
              type="button"
              disabled={disabled}
              className={`px-4 py-2 border border-gray-300 rounded hover:border-blue-400 hover:text-blue-500 transition-colors ${
                dragOver ? 'border-blue-500 bg-blue-50' : ''
              }`}
            >
              <UploadIcon className="inline w-4 h-4 mr-2" />
              Click to Upload
            </button>
          )}
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled}
      />
      {renderFileList()}
    </div>
  );
};

// Icons
const UploadIcon = ({ className = '' }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const FileIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
  </svg>
);

const CheckIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
  </svg>
);

const ErrorIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
  </svg>
);

const TrashIcon = ({ className = '' }: { className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);
