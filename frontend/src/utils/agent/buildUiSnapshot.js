function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

export default function buildUiSnapshot({
  pathname = '/home',
  mode = 'home',
  locationState = null,
  visibleSections = [],
  selectedEntities = {},
  filters = {},
  portfolioSummary = null,
} = {}) {
  return {
    route: pathname,
    mode,
    visible_sections: Array.isArray(visibleSections) ? visibleSections : [],
    selected_entities: {
      stock_code: selectedEntities.stock_code || null,
      stock_name: selectedEntities.stock_name || null,
      date_key: selectedEntities.date_key || null,
      case_id: selectedEntities.case_id || null,
    },
    filters: {
      period: filters.period || null,
      tab: filters.tab || null,
      keyword: filters.keyword || null,
    },
    portfolio_summary: portfolioSummary
      ? {
          total_value: toFiniteNumber(portfolioSummary.total_value),
          current_cash: toFiniteNumber(portfolioSummary.current_cash),
          total_profit_loss_pct: toFiniteNumber(portfolioSummary.total_profit_loss_pct),
          holdings_count: toFiniteNumber(portfolioSummary.holdings_count),
        }
      : null,
    location_state: locationState || null,
    captured_at: new Date().toISOString(),
  };
}
