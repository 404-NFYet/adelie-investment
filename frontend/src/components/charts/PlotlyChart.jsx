/**
 * PlotlyChart.jsx - Plotly.js 차트 래퍼
 * 동적 로딩으로 번들 사이즈 최적화
 */
import { useState, useEffect, lazy, Suspense } from 'react';

// Plotly.js 동적 로딩
const Plot = lazy(() => import('react-plotly.js'));

const DEFAULT_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: {
    family: 'Inter, Noto Sans KR, sans-serif',
    color: '#4E5968',
    size: 11,
  },
  margin: { t: 40, r: 20, b: 40, l: 50 },
  showlegend: false,
  xaxis: {
    gridcolor: '#F2F4F6',
    linecolor: '#E5E8EB',
  },
  yaxis: {
    gridcolor: '#F2F4F6',
    linecolor: '#E5E8EB',
  },
};

const DEFAULT_CONFIG = {
  displayModeBar: false,
  responsive: true,
};

export default function PlotlyChart({ data, layout, config, className = '' }) {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className={`h-48 bg-gray-50 dark:bg-gray-800/50 rounded-xl flex items-center justify-center ${className}`}>
        <p className="text-xs text-gray-400">차트 데이터 없음</p>
      </div>
    );
  }

  const mergedLayout = {
    ...DEFAULT_LAYOUT,
    ...layout,
    autosize: true,
  };

  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  return (
    <div className={`w-full ${className}`}>
      {isReady && (
        <Suspense
          fallback={
            <div className="h-48 bg-gray-50 dark:bg-gray-800/50 rounded-xl animate-pulse" />
          }
        >
          <Plot
            data={data}
            layout={mergedLayout}
            config={mergedConfig}
            useResizeHandler={true}
            style={{ width: '100%', height: '200px' }}
          />
        </Suspense>
      )}
    </div>
  );
}
