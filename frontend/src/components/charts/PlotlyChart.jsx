/**
 * PlotlyChart.jsx - 레거시 호환 래퍼
 * 내부적으로 공통 ResponsivePlotly 렌더러를 사용
 */
import ResponsivePlotly from './ResponsivePlotly';

export default function PlotlyChart({ data, layout, config, className = '' }) {
  return (
    <ResponsivePlotly
      data={data}
      layout={layout}
      config={config}
      mode="fixed"
      fixedHeight={200}
      minHeight={200}
      maxHeight={200}
      className={className}
      loadingText="차트 로딩 중..."
      emptyText="차트 데이터 없음"
    />
  );
}
