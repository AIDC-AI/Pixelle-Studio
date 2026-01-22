import { useState, useEffect, useRef, useCallback } from 'react';

interface VirtualListOptions {
  itemHeight: number; // 预估的每项高度
  overscan?: number; // 上下额外渲染的项数
  containerHeight?: number; // 容器高度，不传则自动计算
}

interface VirtualListResult<T> {
  virtualItems: Array<{
    index: number;
    data: T;
    offsetTop: number;
  }>;
  totalHeight: number;
  containerRef: React.RefObject<HTMLDivElement>;
  scrollToIndex: (index: number, behavior?: ScrollBehavior) => void;
  scrollToBottom: (behavior?: ScrollBehavior) => void;
}

export function useVirtualList<T>(
  items: T[],
  options: VirtualListOptions
): VirtualListResult<T> {
  const { itemHeight, overscan = 3, containerHeight: fixedHeight } = options;
  
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(fixedHeight || 600);
  const itemHeightsRef = useRef<Map<number, number>>(new Map());

  // 监听容器高度变化
  useEffect(() => {
    if (fixedHeight) return;
    
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [fixedHeight]);

  // 监听滚动
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (container) {
      setScrollTop(container.scrollTop);
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  // 计算可见范围
  const { startIndex, endIndex, virtualItems, totalHeight } = useCallback(() => {
    if (items.length === 0) {
      return {
        startIndex: 0,
        endIndex: 0,
        virtualItems: [],
        totalHeight: 0,
      };
    }

    let offsetTop = 0;
    let startIndex = 0;
    let endIndex = 0;
    const virtualItems: Array<{ index: number; data: T; offsetTop: number }> = [];

    // 找到起始索引
    for (let i = 0; i < items.length; i++) {
      const height = itemHeightsRef.current.get(i) || itemHeight;
      if (offsetTop + height > scrollTop) {
        startIndex = Math.max(0, i - overscan);
        break;
      }
      offsetTop += height;
    }

    // 重新计算起始位置的 offsetTop
    offsetTop = 0;
    for (let i = 0; i < startIndex; i++) {
      offsetTop += itemHeightsRef.current.get(i) || itemHeight;
    }

    // 找到结束索引并构建虚拟项
    const viewportBottom = scrollTop + containerHeight;
    for (let i = startIndex; i < items.length; i++) {
      const height = itemHeightsRef.current.get(i) || itemHeight;
      
      virtualItems.push({
        index: i,
        data: items[i],
        offsetTop,
      });

      offsetTop += height;
      endIndex = i;

      if (offsetTop > viewportBottom + overscan * itemHeight) {
        break;
      }
    }

    // 计算总高度
    let totalHeight = 0;
    for (let i = 0; i < items.length; i++) {
      totalHeight += itemHeightsRef.current.get(i) || itemHeight;
    }

    return { startIndex, endIndex, virtualItems, totalHeight };
  }, [items, scrollTop, containerHeight, itemHeight, overscan])();

  // 滚动到指定索引
  const scrollToIndex = useCallback(
    (index: number, behavior: ScrollBehavior = 'smooth') => {
      const container = containerRef.current;
      if (!container) return;

      let offsetTop = 0;
      for (let i = 0; i < index; i++) {
        offsetTop += itemHeightsRef.current.get(i) || itemHeight;
      }

      container.scrollTo({ top: offsetTop, behavior });
    },
    [itemHeight]
  );

  // 滚动到底部
  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = 'smooth') => {
      const container = containerRef.current;
      if (!container) return;

      container.scrollTo({ top: container.scrollHeight, behavior });
    },
    []
  );

  return {
    virtualItems,
    totalHeight,
    containerRef,
    scrollToIndex,
    scrollToBottom,
  };
}

// 用于测量实际高度的 Hook
export function useMeasure(callback: (height: number) => void) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        callback(entry.contentRect.height);
      }
    });

    resizeObserver.observe(element);
    // 立即测量一次
    callback(element.getBoundingClientRect().height);

    return () => resizeObserver.disconnect();
  }, [callback]);

  return ref;
}
