const BASE_MARGIN = { l: 32, r: 14, t: 20, b: 36 };
const PIE_MARGIN = { l: 10, r: 10, t: 22, b: 10 };

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function isDateLike(value) {
  if (value instanceof Date) return Number.isFinite(value.getTime());
  if (typeof value !== 'string') return false;
  return Number.isFinite(Date.parse(value));
}

function isValidRange(range) {
  if (!Array.isArray(range) || range.length !== 2) return false;

  const [start, end] = range;
  const bothFinite = isFiniteNumber(start) && isFiniteNumber(end);
  if (bothFinite) return start !== end;

  const bothDate = isDateLike(start) && isDateLike(end);
  if (bothDate) return Date.parse(start) !== Date.parse(end);

  return false;
}

function isValidDomain(domain) {
  if (!Array.isArray(domain) || domain.length !== 2) return false;
  const [start, end] = domain;
  return isFiniteNumber(start) && isFiniteNumber(end) && start >= 0 && end <= 1 && start < end;
}

function sanitizeAxis(axis, { defaultTickSize = 9 } = {}) {
  const source = axis && typeof axis === 'object' ? { ...axis } : {};

  if (!isValidRange(source.range)) {
    delete source.range;
  }

  if (!isValidDomain(source.domain)) {
    delete source.domain;
  }

  const tickfont = source.tickfont && typeof source.tickfont === 'object' ? source.tickfont : {};

  return {
    ...source,
    automargin: true,
    tickfont: {
      size: defaultTickSize,
      color: '#6B7280',
      ...tickfont,
    },
  };
}

function sanitizeMargin(margin, fallbackMargin) {
  if (!margin || typeof margin !== 'object') return fallbackMargin;

  return {
    l: isFiniteNumber(margin.l) ? margin.l : fallbackMargin.l,
    r: isFiniteNumber(margin.r) ? margin.r : fallbackMargin.r,
    t: isFiniteNumber(margin.t) ? margin.t : fallbackMargin.t,
    b: isFiniteNumber(margin.b) ? margin.b : fallbackMargin.b,
  };
}

export function normalizeLayout(layout, { hasPie = false, clearTitle = false } = {}) {
  const source = layout && typeof layout === 'object' ? { ...layout } : {};

  delete source.width;
  delete source.height;
  delete source.responsive;
  delete source.autosize;

  if (clearTitle) {
    delete source.title;
  }

  const xaxis = sanitizeAxis(source.xaxis, { defaultTickSize: 9 });
  const yaxis = sanitizeAxis(source.yaxis, { defaultTickSize: 9 });

  const base = {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: {
      family: 'IBM Plex Sans KR, Inter, sans-serif',
      size: 10,
      color: '#1F2937',
    },
    showlegend: hasPie,
    legend: hasPie
      ? { orientation: 'h', y: -0.12, x: 0.5, xanchor: 'center' }
      : { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' },
  };

  const normalized = {
    ...base,
    ...source,
    margin: sanitizeMargin(source.margin, hasPie ? PIE_MARGIN : BASE_MARGIN),
  };

  if (hasPie) {
    delete normalized.xaxis;
    delete normalized.yaxis;
  } else {
    normalized.xaxis = {
      showgrid: false,
      zeroline: false,
      tickangle: -20,
      ...xaxis,
    };

    normalized.yaxis = {
      showgrid: true,
      gridcolor: 'rgba(107,114,128,0.16)',
      zeroline: false,
      ...yaxis,
    };
  }

  if (clearTitle) {
    normalized.title = undefined;
  }

  return normalized;
}
