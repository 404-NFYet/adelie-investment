/**
 * PlotlyChart.jsx - Plotly.js 차트 래퍼
 * 동적 로딩으로 번들 사이즈 최적화
 */
import { useState, useEffect, lazy, Suspense } from 'react';

// Plotly.js 동적 로딩
const Plot = lazy(() => import('react-plotly.js'));

/* ── CSS 변수에서 색상 읽기 (다크 모드 대응) ── */
function getCSSVar(name, fallback) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function buildDefaultLayout() {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: {
      family: 'Inter, Noto Sans KR, sans-serif',
      color: getCSSVar('--color-text-secondary', '#4E5968'),
      size: 11,
    },
    margin: { t: 30, r: 15, b: 50, l: 55 },
    showlegend: false,
    xaxis: {
      gridcolor: getCSSVar('--color-border-light', '#F2F4F6'),
      linecolor: getCSSVar('--color-border', '#E5E8EB'),
      automargin: true,
      tickangle: -30,
      tickfont: { size: 9 },
    },
    yaxis: {
      gridcolor: getCSSVar('--color-border-light', '#F2F4F6'),
      linecolor: getCSSVar('--color-border', '#E5E8EB'),
      automargin: true,
      tickfont: { size: 9 },
      separatethousands: true,
    },
  };
}

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
    ...buildDefaultLayout(),
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
