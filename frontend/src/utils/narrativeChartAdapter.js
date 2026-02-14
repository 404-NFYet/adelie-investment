function toFiniteNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/,/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeXYTrace(trace) {
  const sourceY = Array.isArray(trace?.y) ? trace.y : [];
  const sourceX = Array.isArray(trace?.x) ? trace.x : [];

  if (!sourceY.length) return null;

  const points = [];
  for (let idx = 0; idx < sourceY.length; idx += 1) {
    const y = toFiniteNumber(sourceY[idx]);
    if (y === null) continue;
    points.push({ x: sourceX[idx] ?? `${idx + 1}`, y });
  }

  if (!points.length) return null;

  return {
    ...trace,
    x: points.map((p) => p.x),
    y: points.map((p) => p.y),
  };
}

function normalizePieTrace(trace) {
  const values = Array.isArray(trace?.values) ? trace.values : [];
  const labels = Array.isArray(trace?.labels) ? trace.labels : [];

  const points = [];
  for (let idx = 0; idx < values.length; idx += 1) {
    const value = toFiniteNumber(values[idx]);
    if (value === null) continue;
    points.push({ label: labels[idx] ?? `${idx + 1}`, value });
  }

  if (!points.length) return null;

  return {
    ...trace,
    labels: points.map((p) => p.label),
    values: points.map((p) => p.value),
  };
}

function normalizeIncomingTraces(data) {
  if (!Array.isArray(data)) return [];

  return data
    .map((trace) => {
      if (!trace || typeof trace !== 'object') return null;
      if (trace.type === 'pie') return normalizePieTrace(trace);
      return normalizeXYTrace(trace);
    })
    .filter(Boolean);
}

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

function buildBaseLayout(layout = {}, { hasPie = false } = {}) {
  const base = {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: hasPie
      ? { l: 8, r: 8, t: 22, b: 8 }
      : { l: 36, r: 16, t: 24, b: 30 },
    font: {
      family: 'IBM Plex Sans KR, Inter, sans-serif',
      size: 11,
      color: '#1F2937',
    },
    xaxis: hasPie
      ? undefined
      : {
          showgrid: false,
          zeroline: false,
          tickfont: { size: 10, color: '#6B7280' },
        },
    yaxis: hasPie
      ? undefined
      : {
          showgrid: true,
          gridcolor: 'rgba(107,114,128,0.16)',
          zeroline: false,
          tickfont: { size: 10, color: '#6B7280' },
        },
    legend: hasPie
      ? { orientation: 'h', y: -0.12, x: 0.5, xanchor: 'center' }
      : { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' },
    showlegend: hasPie,
  };

  return {
    ...base,
    ...layout,
    title: undefined,
  };
}

export function buildNarrativePlot(stepKey, chart) {
  const traces = normalizeIncomingTraces(chart?.data);
  const resolvedTraces = traces.length > 0 ? traces : convertDataPointsToTrace(chart);
  const finalTraces = resolvedTraces.length > 0 ? resolvedTraces : fallbackTrace(stepKey);

  const hasPie = finalTraces.some((trace) => trace.type === 'pie');

  return {
    data: finalTraces,
    layout: buildBaseLayout(chart?.layout || {}, { hasPie }),
    title: chart?.title || chart?.layout?.title || '',
    annotation: chart?.annotation || '',
  };
}
