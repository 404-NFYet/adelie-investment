/**
 * Charts module - 차트 렌더링 팩토리 및 컨테이너
 * 다양한 차트 타입을 지원하는 범용 차트 시스템
 */

/**
 * ChartContainer - 차트를 감싸는 컨테이너 컴포넌트
 */
export function ChartContainer({ children, className = '' }) {
  return (
    <div className={`w-full rounded-[24px] bg-surface p-4 ${className}`}>
      {children}
    </div>
  );
}

/**
 * 단일 바 차트
 */
function SingleBarChart({ data_points = [], unit }) {
  if (!data_points || data_points.length === 0) return <p className="text-xs text-text-secondary">데이터 없음</p>;
  const maxVal = Math.max(...data_points.map(d => d.value)) || 1;
  return (
    <div className="space-y-3">
      {unit && <p className="text-xs text-text-secondary mb-2">{unit}</p>}
      {data_points.map((d, i) => (
        <div key={i} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-text-primary font-medium">{d.label}</span>
            <span className="text-text-secondary">{d.value}</span>
          </div>
          <div className="w-full h-6 bg-border-light rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(d.value / maxVal) * 100}%`,
                backgroundColor: d.color || '#FF6B00',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * 비교 바 차트
 */
function ComparisonBarChart({ data_points = [], unit }) {
  if (!data_points || data_points.length === 0) return <p className="text-xs text-text-secondary">데이터 없음</p>;
  const maxVal = Math.max(...data_points.map(d => d.value)) || 1;
  return (
    <div className="space-y-3">
      {unit && <p className="text-xs text-text-secondary mb-2">{unit}</p>}
      {data_points.map((d, i) => (
        <div key={i} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-text-primary font-medium">{d.label}</span>
            <span className="text-text-secondary">{d.value}</span>
          </div>
          <div className="w-full h-8 bg-border-light rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(d.value / maxVal) * 100}%`,
                backgroundColor: d.color || '#FF6B00',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * 트렌드 라인 차트 (SVG 기반)
 */
function TrendLineChart({ data_points = [], unit }) {
  if (!data_points || data_points.length < 2) return <p className="text-xs text-text-secondary">데이터 없음</p>;
  const maxVal = Math.max(...data_points.map(d => d.value));
  const minVal = Math.min(...data_points.map(d => d.value));
  const range = maxVal - minVal || 1;
  const w = 320, h = 160;
  const pad = { top: 20, right: 20, bottom: 30, left: 10 };
  const cW = w - pad.left - pad.right;
  const cH = h - pad.top - pad.bottom;

  const pts = data_points.map((d, i) => ({
    x: pad.left + (i / (data_points.length - 1)) * cW,
    y: pad.top + cH - ((d.value - minVal) / range) * cH,
    ...d,
  }));

  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const area = `${line} L ${pts[pts.length - 1].x} ${pad.top + cH} L ${pts[0].x} ${pad.top + cH} Z`;

  return (
    <div>
      {unit && <p className="text-xs text-text-secondary mb-2">{unit}</p>}
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FF6B00" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#FF6B00" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#areaGrad)" />
        <path d={line} fill="none" stroke="#FF6B00" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="4" fill="#FF6B00" />
            <text x={p.x} y={pad.top + cH + 16} textAnchor="middle" fontSize="10" fill="var(--color-text-secondary)">{p.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

/**
 * 리스크 인디케이터 차트
 */
function RiskIndicatorChart({ data_points = [], unit, annotation }) {
  if (!data_points || data_points.length < 2) return <p className="text-xs text-text-secondary">데이터 없음</p>;
  const maxVal = Math.max(...data_points.map(d => d.value));
  const minVal = Math.min(...data_points.map(d => d.value));
  const range = maxVal - minVal || 1;
  const w = 320, h = 160;
  const pad = { top: 24, right: 20, bottom: 30, left: 10 };
  const cW = w - pad.left - pad.right;
  const cH = h - pad.top - pad.bottom;

  const pts = data_points.map((d, i) => ({
    x: pad.left + (i / (data_points.length - 1)) * cW,
    y: pad.top + cH - ((d.value - minVal) / range) * cH,
    ...d,
  }));

  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  return (
    <div>
      {unit && <p className="text-xs text-text-secondary mb-2">{unit}</p>}
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
        <path d={line} fill="none" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="4" fill="#EF4444" />
            <text x={p.x} y={pad.top + cH + 16} textAnchor="middle" fontSize="10" fill="var(--color-text-secondary)">{p.label}</text>
          </g>
        ))}
        {annotation && (
          <text x={w / 2} y={14} textAnchor="middle" fontSize="11" fontWeight="600" fill="#EF4444">{annotation}</text>
        )}
      </svg>
    </div>
  );
}

/**
 * 차트 타입에 따라 적절한 컴포넌트를 렌더링하는 팩토리 함수
 */
export function renderChart(chartType, chartData) {
  switch (chartType) {
    case 'single_bar':
      return <SingleBarChart {...chartData} />;
    case 'comparison_bar':
      return <ComparisonBarChart {...chartData} />;
    case 'trend_line':
      return <TrendLineChart {...chartData} />;
    case 'risk_indicator':
      return <RiskIndicatorChart {...chartData} />;
    default:
      return <SingleBarChart {...chartData} />;
  }
}
