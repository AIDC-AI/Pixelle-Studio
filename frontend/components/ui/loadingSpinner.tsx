import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
  className?: string;
  type?: 'dots' | 'spinner' | 'pulse' | 'bars';
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  color = 'text-gray-300',
  className = '',
  type = 'dots'
}) => {
  const sizeMap = {
    sm: { dot: 'w-1.5 h-1.5', spinner: 'w-4 h-4', bar: 'w-1 h-3' },
    md: { dot: 'w-2 h-2', spinner: 'w-6 h-6', bar: 'w-1.5 h-4' },
    lg: { dot: 'w-3 h-3', spinner: 'w-8 h-8', bar: 'w-2 h-6' },
    xl: { dot: 'w-4 h-4', spinner: 'w-12 h-12', bar: 'w-3 h-8' }
  };

  const sizes = sizeMap[size];

  // 点点点动画
  if (type === 'dots') {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-bounce`}
          style={{ animationDelay: '0ms', animationDuration: '1s' }}
        />
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-bounce`}
          style={{ animationDelay: '150ms', animationDuration: '1s' }}
        />
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-bounce`}
          style={{ animationDelay: '300ms', animationDuration: '1s' }}
        />
      </div>
    );
  }

  // 旋转圆圈
  if (type === 'spinner') {
    return (
      <div className={className}>
        <div 
          className={`${sizes.spinner} border-2 border-gray-200 border-t-current ${color} rounded-full animate-spin`}
        />
      </div>
    );
  }

  // 脉冲动画
  if (type === 'pulse') {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-pulse`}
          style={{ animationDelay: '0ms' }}
        />
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-pulse`}
          style={{ animationDelay: '200ms' }}
        />
        <div 
          className={`${sizes.dot} ${color.replace('text-', 'bg-')} rounded-full animate-pulse`}
          style={{ animationDelay: '400ms' }}
        />
      </div>
    );
  }

  // 条形波浪
  if (type === 'bars') {
    return (
      <div className={`flex items-end gap-1 ${className}`}>
        <div 
          className={`${sizes.bar} ${color.replace('text-', 'bg-')} rounded-sm animate-pulse`}
          style={{ animationDelay: '0ms', animationDuration: '0.8s' }}
        />
        <div 
          className={`${sizes.bar} ${color.replace('text-', 'bg-')} rounded-sm animate-pulse`}
          style={{ animationDelay: '150ms', animationDuration: '0.8s' }}
        />
        <div 
          className={`${sizes.bar} ${color.replace('text-', 'bg-')} rounded-sm animate-pulse`}
          style={{ animationDelay: '300ms', animationDuration: '0.8s' }}
        />
      </div>
    );
  }

  return null;
};

export default LoadingSpinner;
