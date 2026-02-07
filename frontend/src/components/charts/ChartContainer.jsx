/**
 * ChartContainer.jsx - 차트 래퍼 컨테이너
 * 스텝별 차트 또는 플레이스홀더를 표시
 */
import PlotlyChart from './PlotlyChart';
import StepPlaceholder from './StepPlaceholder';

export default function ChartContainer({ chartData, stepKey, color, className = '' }) {
  // 유효한 차트 데이터가 있는지 확인 (빈 데이터/0값만 있는 경우도 무효 처리)
  const hasValidData = (() => {
    if (!chartData?.data || !Array.isArray(chartData.data) || chartData.data.length === 0) return false;
    // x축 데이터 존재 여부
    const firstTrace = chartData.data[0];
    if (!firstTrace?.x?.length) return false;
    // y값이 전부 없거나 0인 경우 무효 처리
    const hasRealY = chartData.data.some(trace =>
      Array.isArray(trace.y) && trace.y.some(v => v !== null && v !== undefined && v !== 0)
    );
    return hasRealY;
  })();

  if (!hasValidData) {
    return <StepPlaceholder stepKey={stepKey} color={color} className={className} />;
  }

  return (
    <div className={`rounded-xl overflow-hidden bg-white/50 dark:bg-gray-800/30 p-3 ${className}`}>
      <PlotlyChart
        data={chartData.data}
        layout={chartData.layout}
      />
    </div>
  );
}
