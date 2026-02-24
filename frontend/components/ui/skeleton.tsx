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

import React from 'react';

interface SkeletonProps {
  active?: boolean;
  avatar?: boolean | { size?: 'small' | 'default' | 'large'; shape?: 'circle' | 'square' };
  paragraph?: boolean | { rows?: number; width?: string | string[] };
  title?: boolean | { width?: string };
  loading?: boolean;
  children?: React.ReactNode;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  active = false,
  avatar = false,
  paragraph = true,
  title = true,
  loading = true,
  children,
  className = '',
}) => {
  if (!loading) {
    return <>{children}</>;
  }

  const animationClass = active ? 'animate-pulse' : '';

  // Avatar config
  const avatarConfig = typeof avatar === 'object' ? avatar : {};
  const avatarSize = avatarConfig.size || 'default';
  const avatarShape = avatarConfig.shape || 'circle';
  
  const avatarSizeMap = {
    small: 'w-8 h-8',
    default: 'w-10 h-10',
    large: 'w-12 h-12',
  };

  // Title config
  const titleConfig = typeof title === 'object' ? title : {};
  const titleWidth = titleConfig.width || '38%';

  // Paragraph config
  const paragraphConfig = typeof paragraph === 'object' ? paragraph : {};
  const paragraphRows = paragraphConfig.rows || 3;
  const paragraphWidth = paragraphConfig.width;

  const getRowWidth = (index: number) => {
    if (Array.isArray(paragraphWidth)) {
      return paragraphWidth[index] || '100%';
    }
    if (typeof paragraphWidth === 'string') {
      return paragraphWidth;
    }
    // Default widths
    if (index === paragraphRows - 1) {
      return '61%';
    }
    return '100%';
  };

  return (
    <div className={`flex gap-4 ${className}`}>
      {avatar && (
        <div
          className={`${avatarSizeMap[avatarSize]} ${
            avatarShape === 'circle' ? 'rounded-full' : 'rounded'
          } bg-gray-200 ${animationClass} flex-shrink-0`}
        />
      )}
      
      <div className="flex-1 space-y-3">
        {title && (
          <div
            className={`h-4 bg-gray-200 rounded ${animationClass}`}
            style={{ width: titleWidth }}
          />
        )}
        
        {paragraph && (
          <div className="space-y-2">
            {Array.from({ length: paragraphRows }).map((_, index) => (
              <div
                key={index}
                className={`h-4 bg-gray-200 rounded ${animationClass}`}
                style={{ width: getRowWidth(index) }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Additional variants
export const SkeletonButton: React.FC<{
  active?: boolean;
  size?: 'small' | 'default' | 'large';
  shape?: 'default' | 'circle' | 'round';
  className?: string;
}> = ({ active = false, size = 'default', shape = 'default', className = '' }) => {
  const sizeMap = {
    small: 'h-6 w-16',
    default: 'h-8 w-20',
    large: 'h-10 w-24',
  };

  const shapeMap = {
    default: 'rounded',
    circle: 'rounded-full w-8 h-8',
    round: 'rounded-full',
  };

  return (
    <div
      className={`${sizeMap[size]} ${shapeMap[shape]} bg-gray-200 ${
        active ? 'animate-pulse' : ''
      } ${className}`}
    />
  );
};

export const SkeletonInput: React.FC<{
  active?: boolean;
  size?: 'small' | 'default' | 'large';
  className?: string;
}> = ({ active = false, size = 'default', className = '' }) => {
  const sizeMap = {
    small: 'h-6',
    default: 'h-8',
    large: 'h-10',
  };

  return (
    <div
      className={`${sizeMap[size]} w-full bg-gray-200 rounded ${
        active ? 'animate-pulse' : ''
      } ${className}`}
    />
  );
};

export const SkeletonImage: React.FC<{
  active?: boolean;
  className?: string;
}> = ({ active = false, className = '' }) => {
  return (
    <div
      className={`w-full h-full bg-gray-200 rounded flex items-center justify-center ${
        active ? 'animate-pulse' : ''
      } ${className}`}
    >
      <svg
        className="w-12 h-12 text-gray-400"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  );
};
