function isDateLike(value) {
  if (value instanceof Date) return Number.isFinite(value.getTime());
  if (typeof value !== 'string') return false;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed);
}

export function toFiniteNumber(value) {
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
    points.push({
      x: sourceX[idx] ?? `${idx + 1}`,
      y,
    });
  }

  if (!points.length) return null;

  const shouldSortByDate =
    trace?.type === 'scatter' &&
    typeof trace?.mode === 'string' &&
    trace.mode.includes('line') &&
    points.every((point) => isDateLike(point.x));

  if (shouldSortByDate) {
    points.sort((a, b) => Date.parse(a.x) - Date.parse(b.x));
  }

  return {
    ...trace,
    x: points.map((point) => point.x),
    y: points.map((point) => point.y),
  };
}

function normalizePieTrace(trace) {
  const values = Array.isArray(trace?.values) ? trace.values : [];
  const labels = Array.isArray(trace?.labels) ? trace.labels : [];

  const points = [];
  for (let idx = 0; idx < values.length; idx += 1) {
    const value = toFiniteNumber(values[idx]);
    if (value === null) continue;
    points.push({
      label: labels[idx] ?? `${idx + 1}`,
      value,
    });
  }

  if (!points.length) return null;

  return {
    ...trace,
    labels: points.map((point) => point.label),
    values: points.map((point) => point.value),
  };
}

function normalizeSingleTrace(trace) {
  if (!trace || typeof trace !== 'object') return null;
  if (trace.type === 'pie') return normalizePieTrace(trace);
  return normalizeXYTrace(trace);
}

export function normalizeTraces(data, { fallbackTraces = [] } = {}) {
  const source = Array.isArray(data) ? data : [];
  const normalized = source.map(normalizeSingleTrace).filter(Boolean);
  if (normalized.length > 0) return normalized;

  const fallback = Array.isArray(fallbackTraces) ? fallbackTraces : [];
  return fallback.map(normalizeSingleTrace).filter(Boolean);
}
