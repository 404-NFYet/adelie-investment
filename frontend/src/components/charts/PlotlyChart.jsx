/**
 * PlotlyChart.jsx - Plotly.js 차트 래퍼 (adelie_fe_test 스타일 적용)
 * 동적 로딩으로 번들 사이즈 최적화
 */
import { useState, useEffect, useMemo, lazy, Suspense } from 'react';
import { BarChart3 } from 'lucide-react';

// Plotly.js 동적 로딩
const Plot = lazy(() => import('react-plotly.js'));

const getDefaultLayout = (traceCount, layout) => {
  // 다중 트레이스 레전드 설정
  const hasMultipleTraces = traceCount >= 2;
  const legendConfig = hasMultipleTraces
    ? { showlegend: true, legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' } }
    : { showlegend: false };

  return {
    autosize: true,
    height: undefined,
    width: undefined,
    margin: { t: 40, b: hasMultipleTraces ? 60 : 50, l: 50, r: 20 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: {
      family: 'IBM Plex Sans KR, IBM Plex Sans, Inter, Noto Sans KR, sans-serif',
      color: '#4E5968',
      size: 10,
    },
    ...legendConfig,
    xaxis: {
      title: { text: layout?.xaxis?.title?.text || '', font: { size: 10, weight: 'bold' } },
      showgrid: false,
      zeroline: false,
      color: '#8B95A1',
      tickfont: { size: 9 },
      automargin: true,
    },
    yaxis: {
      title: { text: layout?.yaxis?.title?.text || '', font: { size: 10, weight: 'bold' } },
      showgrid: true,
      gridcolor: '#F2F4F6',
      zeroline: false,
      color: '#8B95A1',
      tickfont: { size: 9 },
      automargin: true,
      separatethousands: true,
    },
    ...layout,
    // 레전드 강제 오버라이드
    ...(hasMultipleTraces ? { 
      showlegend: true, 
      legend: { 
        ...(layout?.legend || {}), 
        orientation: 'h', 
        y: -0.2, 
        x: 0.5, 
        xanchor: 'center' 
      } 
    } : {}),
  };
};

const DEFAULT_CONFIG = {
  displayModeBar: false,
  responsive: true,
  staticPlot: false,
};

export default function PlotlyChart({ data, layout, config, className = '' }) {
  const [isReady, setIsReady] = useState(false);
  const traceCount = Array.isArray(data) ? data.length : 0;

  useEffect(() => {
    setIsReady(true);
  }, []);

  const mergedLayout = useMemo(() => {
    return getDefaultLayout(traceCount, layout);
  }, [layout, traceCount]);

  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center h-full min-h-[160px] text-[#ADB5BD] text-xs font-medium ${className}`}>
        <BarChart3 className="w-5 h-5 mb-2 opacity-50" />
        <span>차트 데이터를 준비 중입니다...</span>
      </div>
    );
  }

  return (
    <div className={`w-full h-full min-h-[160px] flex items-center justify-center ${className}`}>
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
            className="w-full h-full"
            style={{ width: '100%', height: '100%' }}
          />
        </Suspense>
      )}
    </div>
  );
}
