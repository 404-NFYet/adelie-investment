/**
 * charts/index.js - 차트 컴포넌트 시스템
 * Plotly.js + Chart.js 기반 차트 렌더링
 */

export { default as PlotlyChart } from './PlotlyChart';
export { default as ChartContainer } from './ChartContainer';
export { default as StepPlaceholder } from './StepPlaceholder';

/**
 * 차트 데이터를 렌더링할 적절한 컴포넌트를 결정
 * @param {object} chartData - { data, layout } Plotly 형식
 * @returns {string} - 'plotly' | 'bar' | 'placeholder'
 */
export function getChartType(chartData) {
  if (!chartData || !chartData.data || !Array.isArray(chartData.data)) {
    return 'placeholder';
  }
  const firstTrace = chartData.data[0];
  if (!firstTrace) return 'placeholder';
  if (firstTrace.type === 'bar') return 'bar';
  return 'plotly';
}

/**
 * 차트 데이터를 렌더링
 * @param {object} chartData - Plotly.js 호환 차트 데이터
 * @param {string} stepKey - 현재 스텝 키
 * @param {string} color - 스텝 색상
 */
export function renderChart(chartData, stepKey, color) {
  // 이 함수는 JSX를 반환하지 않음 - 컴포넌트를 직접 사용하세요
  // PlotlyChart, ChartContainer 참조
  return { chartData, stepKey, color, type: getChartType(chartData) };
}
