import React, { useEffect, useMemo, useRef, useState } from 'react';

const EChart = React.lazy(() => import('echarts-for-react'));

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

class EChartErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex items-center justify-center text-sm text-text-secondary"
          style={{ height: this.props.height }}
        >
          {this.props.emptyText}
        </div>
      );
    }

    return this.props.children;
  }
}

export default function ResponsiveEChart({
  option,
  mode = 'ratio',
  ratio = 1.16,
  minHeight = 220,
  maxHeight = 460,
  fixedHeight = 280,
  className = '',
  loadingText = '차트 로딩 중...',
  emptyText = '차트 데이터가 없습니다',
}) {
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return undefined;

    const updateSize = () => {
      setContainerWidth(element.clientWidth || 0);
    };

    updateSize();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateSize);
      return () => window.removeEventListener('resize', updateSize);
    }

    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries?.[0]?.contentRect?.width || element.clientWidth || 0;
      setContainerWidth(nextWidth);
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const resolvedHeight = useMemo(() => {
    if (mode === 'fixed') {
      return Math.max(120, Math.round(fixedHeight));
    }

    const nextHeight = Math.round((containerWidth || minHeight) * ratio);
    return clamp(nextHeight, minHeight, maxHeight);
  }, [containerWidth, fixedHeight, maxHeight, minHeight, mode, ratio]);

  const hasSeries = Array.isArray(option?.series) && option.series.length > 0;

  const chartKey = useMemo(
    () => `echart-${mode}-${Math.round(containerWidth)}-${resolvedHeight}-${hasSeries ? option.series.length : 0}`,
    [containerWidth, hasSeries, mode, option?.series?.length, resolvedHeight],
  );

  const mergedOption = useMemo(() => ({
    animation: false,
    ...(option || {}),
  }), [option]);

  return (
    <div ref={containerRef} className={`w-full ${className}`}>
      <EChartErrorBoundary height={resolvedHeight} emptyText={emptyText}>
        <React.Suspense
          fallback={(
            <div className="flex items-center justify-center text-sm text-text-secondary" style={{ height: resolvedHeight }}>
              {loadingText}
            </div>
          )}
        >
          <div className="w-full" style={{ height: resolvedHeight }}>
            {hasSeries ? (
              <EChart
                key={chartKey}
                option={mergedOption}
                style={{ width: '100%', height: '100%' }}
                notMerge
                lazyUpdate
                opts={{ renderer: 'canvas' }}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-secondary">
                {emptyText}
              </div>
            )}
          </div>
        </React.Suspense>
      </EChartErrorBoundary>
    </div>
  );
}
