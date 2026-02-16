import { normalizeLayout } from './plotly/normalizeLayout';
import { normalizeTraces, toFiniteNumber } from './plotly/normalizeTraces';

function convertDataPointsToTrace(chart) {
  const type = (chart?.chart_type || '').toLowerCase();
  const points = Array.isArray(chart?.data_points) ? chart.data_points : [];

  const normalized = points
    .map((point, idx) => ({
      label: point?.label ?? `${idx + 1}`,
      value: toFiniteNumber(point?.value),
      color: point?.color,
    }))
    .filter((point) => point.value !== null);

  if (!normalized.length) return [];

  const labels = normalized.map((point) => point.label);
  const values = normalized.map((point) => point.value);

  if (type.includes('bar')) {
    return [{
      type: 'bar',
      x: labels,
      y: values,
      marker: {
        color: normalized.map((point) => point.color || '#FF6B00'),
        opacity: 0.9,
      },
      hovertemplate: '%{x}: %{y}<extra></extra>',
    }];
  }

  const lineColor = type.includes('risk') ? '#EF4444' : '#FF6B00';

  return [{
    type: 'scatter',
    mode: 'lines+markers',
    x: labels,
    y: values,
    line: { color: lineColor, width: 2.5, shape: 'spline' },
    marker: { color: lineColor, size: 5 },
    fill: type.includes('risk') ? 'none' : 'tozeroy',
    fillcolor: type.includes('risk') ? 'transparent' : 'rgba(255,107,0,0.15)',
    hovertemplate: '%{x}: %{y}<extra></extra>',
  }];
}

function fallbackTrace(stepKey) {
  const presets = {
    background: [95, 102, 108, 117],
    concept_explain: [100, 104, 103, 109],
    history: [82, 90, 88, 97],
    application: [90, 93, 98, 102],
    summary: [100, 106, 111, 118],
  };

  const values = presets[stepKey] || [96, 99, 103, 107];
  const labels = ['1', '2', '3', '4'];

  return [{
    type: 'scatter',
    mode: 'lines+markers',
    x: labels,
    y: values,
    line: { color: '#FF6B00', width: 2.5, shape: 'spline' },
    marker: { color: '#FF6B00', size: 5 },
    fill: 'tozeroy',
    fillcolor: 'rgba(255,107,0,0.14)',
    hovertemplate: '%{x}: %{y}<extra></extra>',
  }];
}

export function buildNarrativePlot(stepKey, chart) {
  const preferredTraces = normalizeTraces(chart?.data);
  const convertedTraces = normalizeTraces(convertDataPointsToTrace(chart));
  const fallbackTraces = normalizeTraces(fallbackTrace(stepKey));

  const finalTraces = preferredTraces.length > 0
    ? preferredTraces
    : (convertedTraces.length > 0 ? convertedTraces : fallbackTraces);

  const hasPie = finalTraces.some((trace) => trace.type === 'pie');

  return {
    data: finalTraces,
    layout: normalizeLayout(chart?.layout || {}, { hasPie, clearTitle: true }),
    title: chart?.title || chart?.layout?.title || '',
    annotation: chart?.annotation || '',
  };
}
