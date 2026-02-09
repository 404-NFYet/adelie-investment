/**
 * ChartComponent.jsx - Chart.js 기반 내러티브 차트 렌더러
 * Plotly 형식 데이터를 Chart.js 포맷으로 변환하여 렌더링
 * line, bar, candlestick-like 차트 지원
 */
import { useMemo, useRef, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Chart.js 컴포넌트 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

/* ── CSS 변수에서 색상 읽기 ── */
function getCSSVar(name, fallback) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/* ── 기본 색상 팔레트 (CSS 변수 기반, 다크 모드 대응) ── */
function buildPalette() {
  return [
    getCSSVar('--color-primary', '#FF6B00'),
    getCSSVar('--color-info', '#3B82F6'),
    getCSSVar('--color-success', '#10B981'),
    getCSSVar('--color-purple', '#8B5CF6'),
    getCSSVar('--color-danger', '#EF4444'),
    getCSSVar('--color-warning', '#F59E0B'),
    getCSSVar('--color-pink', '#EC4899'),
  ];
}

/* ── Plotly trace → Chart.js dataset 변환 ── */
function convertTrace(trace, index) {
  const palette = buildPalette();
  const color = trace.marker?.color || trace.line?.color || palette[index % palette.length];
  const type = trace.type || 'scatter';

  const baseDataset = {
    label: trace.name || `데이터 ${index + 1}`,
    data: trace.y || [],
  };

  if (type === 'bar') {
    return {
      ...baseDataset,
      backgroundColor: Array.isArray(color) ? color : `${color}CC`,
      borderColor: Array.isArray(color) ? color : color,
      borderWidth: 1,
      borderRadius: 4,
      barPercentage: 0.7,
      categoryPercentage: 0.8,
    };
  }

  // line (scatter 포함)
  return {
    ...baseDataset,
    borderColor: color,
    backgroundColor: `${color}20`,
    pointBackgroundColor: color,
    pointBorderColor: '#fff',
    pointBorderWidth: 1.5,
    pointRadius: 3,
    pointHoverRadius: 5,
    borderWidth: 2.5,
    tension: 0.3,
    fill: trace.fill === 'tozeroy' || trace.fill === 'tonexty',
  };
}

/* ── OHLC/캔들스틱 데이터를 bar+line으로 시뮬레이션 ── */
function buildCandlestickData(trace) {
  const labels = trace.x || [];
  const open = trace.open || [];
  const high = trace.high || [];
  const low = trace.low || [];
  const close = trace.close || [];

  // 상승(양봉): close > open → green, 하락(음봉): close < open → red
  const barColors = close.map((c, i) => (c >= open[i] ? '#10B981' : '#EF4444'));
  const barBorders = [...barColors];

  // 바 차트: open-close 범위 (floating bar 시뮬레이션)
  const barData = close.map((c, i) => Math.abs(c - open[i]));

  return {
    labels,
    datasets: [
      {
        type: 'bar',
        label: '시가-종가',
        data: barData,
        backgroundColor: barColors.map((c) => `${c}99`),
        borderColor: barBorders,
        borderWidth: 1,
        borderRadius: 2,
        barPercentage: 0.6,
      },
      {
        type: 'line',
        label: '고가',
        data: high,
        borderColor: '#10B98160',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [4, 4],
        fill: false,
      },
      {
        type: 'line',
        label: '저가',
        data: low,
        borderColor: '#EF444460',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [4, 4],
        fill: false,
      },
      {
        type: 'line',
        label: '종가',
        data: close,
        borderColor: '#FF6B00',
        borderWidth: 2,
        pointRadius: 2,
        pointBackgroundColor: '#FF6B00',
        fill: false,
        tension: 0.2,
      },
    ],
  };
}

/* ── 공통 Chart.js 옵션 생성 ── */
function buildOptions(layout, chartType) {
  const textColor = getCSSVar('--color-text-secondary', '#6b7280');
  const gridColor = getCSSVar('--color-border-light', '#f3f4f6');
  const titleText = layout?.title?.text || layout?.title || '';

  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: !!titleText,
        text: titleText,
        color: getCSSVar('--color-text-primary', '#1a1a1a'),
        font: {
          family: "'IBM Plex Sans KR', 'Inter', sans-serif",
          size: 12,
          weight: '600',
        },
        padding: { bottom: 8 },
      },
      tooltip: {
        backgroundColor: getCSSVar('--color-surface-elevated', '#ffffff'),
        titleColor: getCSSVar('--color-text-primary', '#1a1a1a'),
        bodyColor: textColor,
        borderColor: getCSSVar('--color-border', '#e5e7eb'),
        borderWidth: 1,
        cornerRadius: 8,
        padding: 10,
        titleFont: { family: "'IBM Plex Sans KR', sans-serif", size: 11, weight: '600' },
        bodyFont: { family: "'IBM Plex Sans KR', sans-serif", size: 11 },
        displayColors: true,
        boxPadding: 4,
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed.y;
            if (val === null || val === undefined) return '';
            // 천 단위 쉼표
            const formatted = typeof val === 'number' ? val.toLocaleString('ko-KR') : val;
            return ` ${ctx.dataset.label}: ${formatted}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: gridColor },
        ticks: {
          color: textColor,
          font: { family: "'IBM Plex Sans KR', sans-serif", size: 9 },
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 8,
        },
      },
      y: {
        grid: {
          color: gridColor,
          drawBorder: false,
        },
        border: { display: false },
        ticks: {
          color: textColor,
          font: { family: "'IBM Plex Sans KR', sans-serif", size: 9 },
          callback: (value) => {
            if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(0)}만`;
            if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(0)}천`;
            return value.toLocaleString('ko-KR');
          },
        },
        beginAtZero: chartType === 'bar',
      },
    },
    animation: {
      duration: 600,
      easing: 'easeOutQuart',
    },
  };
}

/* ── 차트 데이터가 유효한지 검사 ── */
function isValidChartData(chartData) {
  if (!chartData?.data || !Array.isArray(chartData.data) || chartData.data.length === 0) return false;
  const first = chartData.data[0];
  if (!first) return false;
  // x 또는 y 데이터가 있어야 함
  const hasX = first.x && first.x.length > 0;
  const hasY = first.y && first.y.length > 0;
  const hasOHLC = first.open && first.close;
  return hasX || hasY || hasOHLC;
}

/* ══════════════════════════════════════
   ChartComponent - 메인 컴포넌트
   ══════════════════════════════════════ */
export default function ChartComponent({ chartData, stepColor = '#FF6B00', className = '' }) {
  const chartRef = useRef(null);

  // 차트 데이터가 없거나 무효한 경우
  if (!isValidChartData(chartData)) {
    return (
      <div className={`h-[200px] flex items-center justify-center rounded-2xl glass-card ${className}`}>
        <p className="text-xs text-text-muted">차트 데이터를 준비 중입니다...</p>
      </div>
    );
  }

  const traces = chartData.data;
  const layout = chartData.layout || {};

  // 차트 타입 결정
  const isCandlestick = traces.some((t) => t.type === 'candlestick' || t.type === 'ohlc');
  const isBarChart = !isCandlestick && traces.every((t) => t.type === 'bar');
  const chartType = isCandlestick ? 'candlestick' : isBarChart ? 'bar' : 'line';

  // 차트 데이터 변환
  const convertedData = useMemo(() => {
    if (isCandlestick) {
      const ohlcTrace = traces.find((t) => t.type === 'candlestick' || t.type === 'ohlc');
      return buildCandlestickData(ohlcTrace);
    }

    const labels = traces[0]?.x || traces[0]?.y?.map((_, i) => `${i + 1}`) || [];
    const datasets = traces.map((trace, i) => convertTrace(trace, i));

    return { labels, datasets };
  }, [chartData]);

  const options = useMemo(
    () => buildOptions(layout, chartType),
    [layout, chartType],
  );

  // 캔들스틱(복합차트) 또는 바 차트는 Bar, 나머지는 Line
  const ChartComp = (chartType === 'bar' || chartType === 'candlestick') ? Bar : Line;

  return (
    <div className={`relative rounded-2xl overflow-hidden ${className}`}>
      {/* 스텝 색상 악센트 라인 */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl"
        style={{ background: `linear-gradient(90deg, ${stepColor}, ${stepColor}40)` }}
      />
      <div className="p-3 pt-4" style={{ height: '220px' }}>
        <ChartComp ref={chartRef} data={convertedData} options={options} />
      </div>
    </div>
  );
}
