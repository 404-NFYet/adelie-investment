function toFiniteNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/,/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isDateLike(value) {
  if (value instanceof Date) return Number.isFinite(value.getTime());
  if (typeof value !== 'string') return false;
  return Number.isFinite(Date.parse(value));
}

function isNumericLike(value) {
  return toFiniteNumber(value) !== null;
}

function readTitle(title) {
  if (typeof title === 'string') return title;
  if (title && typeof title === 'object' && typeof title.text === 'string') return title.text;
  return '';
}

function normalizePieTrace(trace) {
  const labels = Array.isArray(trace?.labels) ? trace.labels : [];
  const values = Array.isArray(trace?.values) ? trace.values : [];
  const colors = Array.isArray(trace?.marker?.color) ? trace.marker.color : null;

  const points = [];
  for (let idx = 0; idx < values.length; idx += 1) {
    const value = toFiniteNumber(values[idx]);
    if (value === null) continue;
    points.push({
      name: labels[idx] ?? `${idx + 1}`,
      value,
      color: colors?.[idx] ?? null,
    });
  }

  if (!points.length) return null;
  return { ...trace, __points: points };
}

function normalizeXYTrace(trace) {
  const sourceX = Array.isArray(trace?.x) ? trace.x : [];
  const sourceY = Array.isArray(trace?.y) ? trace.y : [];
  if (!sourceY.length) return null;

  const points = [];
  for (let idx = 0; idx < sourceY.length; idx += 1) {
    const y = toFiniteNumber(sourceY[idx]);
    if (y === null) continue;
    points.push({
      x: sourceX[idx] ?? `${idx + 1}`,
      y,
    });
  }

  if (!points.length) return null;
  return { ...trace, __points: points };
}

function normalizeTraces(traces) {
  if (!Array.isArray(traces)) return [];

  return traces
    .map((trace) => {
      if (!trace || typeof trace !== 'object') return null;
      const type = (trace.type || 'scatter').toLowerCase();
      if (type === 'pie') return normalizePieTrace(trace);
      return normalizeXYTrace({ ...trace, type });
    })
    .filter(Boolean);
}

function getTraceColor(trace) {
  if (typeof trace?.line?.color === 'string') return trace.line.color;
  if (typeof trace?.marker?.color === 'string') return trace.marker.color;
  return undefined;
}

function detectXAxisType(traces) {
  const xValues = traces.flatMap((trace) => trace.__points?.map((point) => point.x) || []);
  if (!xValues.length) return 'category';
  if (xValues.every((value) => isDateLike(value))) return 'time';
  if (xValues.every((value) => isNumericLike(value))) return 'value';
  return 'category';
}

function toAxisName(axis) {
  if (!axis || typeof axis !== 'object') return '';
  return readTitle(axis.title);
}

function toCategorySeries(trace, categories, categoryIndexMap) {
  const type = (trace.type || 'scatter').toLowerCase();
  const mode = typeof trace.mode === 'string' ? trace.mode : 'lines';
  const hasLine = mode.includes('lines');
  const hasMarker = mode.includes('markers');
  const color = getTraceColor(trace);

  const baseValues = new Array(categories.length).fill(null);
  trace.__points.forEach((point) => {
    const key = String(point.x);
    const index = categoryIndexMap.get(key);
    if (index !== undefined) baseValues[index] = point.y;
  });

  if (type === 'bar') {
    return {
      name: trace.name || '',
      type: 'bar',
      data: baseValues,
      itemStyle: color ? { color } : undefined,
      barMaxWidth: 24,
    };
  }

  if (!hasLine && hasMarker) {
    return {
      name: trace.name || '',
      type: 'scatter',
      data: baseValues,
      itemStyle: color ? { color } : undefined,
      symbolSize: 6,
    };
  }

  const fill = typeof trace.fill === 'string' ? trace.fill : '';
  const areaStyle = fill.includes('tozero') || fill.includes('tonext')
    ? { opacity: 0.18, color }
    : undefined;

  return {
    name: trace.name || '',
    type: 'line',
    data: baseValues,
    smooth: trace?.line?.shape === 'spline',
    showSymbol: hasMarker,
    lineStyle: {
      width: 2,
      color,
    },
    itemStyle: color ? { color } : undefined,
    areaStyle,
    connectNulls: true,
  };
}

function toValueSeries(trace, axisType) {
  const type = (trace.type || 'scatter').toLowerCase();
  const mode = typeof trace.mode === 'string' ? trace.mode : 'lines';
  const hasLine = mode.includes('lines');
  const hasMarker = mode.includes('markers');
  const color = getTraceColor(trace);

  const values = trace.__points.map((point) => [
    axisType === 'value' ? toFiniteNumber(point.x) : point.x,
    point.y,
  ]).filter(([x]) => x !== null && x !== undefined);

  if (!values.length) return null;

  if (type === 'bar') {
    return {
      name: trace.name || '',
      type: 'bar',
      data: values,
      itemStyle: color ? { color } : undefined,
      barMaxWidth: 24,
    };
  }

  if (!hasLine && hasMarker) {
    return {
      name: trace.name || '',
      type: 'scatter',
      data: values,
      itemStyle: color ? { color } : undefined,
      symbolSize: 6,
    };
  }

  const fill = typeof trace.fill === 'string' ? trace.fill : '';
  const areaStyle = fill.includes('tozero') || fill.includes('tonext')
    ? { opacity: 0.18, color }
    : undefined;

  return {
    name: trace.name || '',
    type: 'line',
    data: values,
    smooth: trace?.line?.shape === 'spline',
    showSymbol: hasMarker,
    lineStyle: {
      width: 2,
      color,
    },
    itemStyle: color ? { color } : undefined,
    areaStyle,
    connectNulls: true,
  };
}

export function canConvertTraces(traces, layout = {}) {
  const normalized = normalizeTraces(traces);
  if (!normalized.length) {
    return { convertible: false, reason: 'empty_traces', traces: [] };
  }

  if (Array.isArray(layout?.grid) || Array.isArray(layout?.xaxis) || Array.isArray(layout?.yaxis)) {
    return { convertible: false, reason: 'subplot_layout', traces: normalized };
  }

  const unsupported = normalized.find((trace) => !['scatter', 'bar', 'pie'].includes(trace.type));
  if (unsupported) {
    return { convertible: false, reason: `unsupported_trace_${unsupported.type}`, traces: normalized };
  }

  const hasPie = normalized.some((trace) => trace.type === 'pie');
  const hasXY = normalized.some((trace) => trace.type !== 'pie');

  if (hasPie && hasXY) {
    return { convertible: false, reason: 'mixed_pie_with_xy', traces: normalized };
  }

  if (hasPie && normalized.length > 1) {
    return { convertible: false, reason: 'multiple_pie_traces', traces: normalized };
  }

  const hasSubplotTrace = normalized.some(
    (trace) => (trace.xaxis && trace.xaxis !== 'x') || (trace.yaxis && trace.yaxis !== 'y'),
  );
  if (hasSubplotTrace) {
    return { convertible: false, reason: 'subplot_trace_axes', traces: normalized };
  }

  return { convertible: true, reason: null, traces: normalized };
}

export function toEChartsOption(traces, layout = {}) {
  const normalized = normalizeTraces(traces);
  if (!normalized.length) {
    return { series: [] };
  }

  const titleText = readTitle(layout?.title);
  const showLegend = layout?.showlegend === true || normalized.length > 1;

  if (normalized[0].type === 'pie') {
    const trace = normalized[0];
    const data = trace.__points.map((point) => ({
      name: point.name,
      value: point.value,
      itemStyle: point.color ? { color: point.color } : undefined,
    }));

    return {
      animation: false,
      backgroundColor: 'transparent',
      title: titleText ? {
        text: titleText,
        left: 'center',
        top: 6,
        textStyle: { fontSize: 12, fontWeight: 600, color: '#374151' },
      } : undefined,
      tooltip: { trigger: 'item' },
      legend: {
        show: showLegend,
        bottom: 0,
        textStyle: { color: '#6B7280', fontSize: 10 },
      },
      series: [{
        type: 'pie',
        radius: ['34%', '66%'],
        center: ['50%', '45%'],
        data,
        label: {
          color: '#4B5563',
          fontSize: 10,
          formatter: '{b}',
        },
      }],
    };
  }

  const axisType = detectXAxisType(normalized);
  const margin = layout?.margin || {};
  const grid = {
    left: Number.isFinite(margin.l) ? margin.l : 32,
    right: Number.isFinite(margin.r) ? margin.r : 14,
    top: Number.isFinite(margin.t) ? margin.t : 20,
    bottom: Number.isFinite(margin.b) ? margin.b : 36,
    containLabel: true,
  };

  let xAxis;
  let series;

  if (axisType === 'category') {
    const categories = [];
    const categoryIndexMap = new Map();

    normalized.forEach((trace) => {
      trace.__points.forEach((point) => {
        const key = String(point.x);
        if (!categoryIndexMap.has(key)) {
          categoryIndexMap.set(key, categories.length);
          categories.push(key);
        }
      });
    });

    xAxis = {
      type: 'category',
      data: categories,
      name: toAxisName(layout?.xaxis),
      nameLocation: 'middle',
      nameGap: 28,
      axisLabel: {
        color: '#6B7280',
        fontSize: 9,
        hideOverlap: true,
      },
      axisLine: { lineStyle: { color: 'rgba(107,114,128,0.35)' } },
      splitLine: { show: false },
      boundaryGap: normalized.some((trace) => trace.type === 'bar'),
    };

    series = normalized.map((trace) => toCategorySeries(trace, categories, categoryIndexMap));
  } else {
    xAxis = {
      type: axisType,
      name: toAxisName(layout?.xaxis),
      nameLocation: 'middle',
      nameGap: 28,
      axisLabel: {
        color: '#6B7280',
        fontSize: 9,
        hideOverlap: true,
      },
      axisLine: { lineStyle: { color: 'rgba(107,114,128,0.35)' } },
      splitLine: { show: false },
      boundaryGap: normalized.some((trace) => trace.type === 'bar'),
    };

    series = normalized
      .map((trace) => toValueSeries(trace, axisType))
      .filter(Boolean);
  }

  return {
    animation: false,
    backgroundColor: 'transparent',
    title: titleText ? {
      text: titleText,
      left: 'center',
      top: 2,
      textStyle: { fontSize: 12, fontWeight: 600, color: '#374151' },
    } : undefined,
    tooltip: { trigger: 'axis' },
    legend: {
      show: showLegend,
      top: 0,
      textStyle: { color: '#6B7280', fontSize: 10 },
    },
    grid,
    xAxis,
    yAxis: {
      type: 'value',
      name: toAxisName(layout?.yaxis),
      nameLocation: 'middle',
      nameGap: 40,
      axisLabel: {
        color: '#6B7280',
        fontSize: 9,
      },
      axisLine: { lineStyle: { color: 'rgba(107,114,128,0.35)' } },
      splitLine: {
        show: true,
        lineStyle: { color: 'rgba(107,114,128,0.18)' },
      },
    },
    series,
  };
}

export function convertPlotlyToECharts(data, layout = {}) {
  const eligibility = canConvertTraces(data, layout);
  if (!eligibility.convertible) {
    return {
      convertible: false,
      reason: eligibility.reason,
      option: null,
    };
  }

  return {
    convertible: true,
    reason: null,
    option: toEChartsOption(eligibility.traces, layout),
  };
}
