function pickAssistantText(messages) {
  if (!Array.isArray(messages)) return '';
  for (let idx = messages.length - 1; idx >= 0; idx -= 1) {
    const message = messages[idx];
    if (message?.role === 'assistant' && typeof message.content === 'string' && message.content.trim()) {
      return message.content.trim();
    }
  }
  return '';
}

function splitParagraphs(text) {
  if (!text) return [];
  return text
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitSentences(text) {
  if (!text) return [];
  return text
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function extractBullets(text, fallbackSentences) {
  const fromLines = String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /^([\-•*]|\d+\.)\s+/.test(line))
    .map((line) => line.replace(/^([\-•*]|\d+\.)\s+/, '').trim())
    .filter(Boolean);

  if (fromLines.length > 0) {
    return fromLines.slice(0, 3);
  }

  return fallbackSentences.slice(2, 5).map((line) => line.replace(/\s+/g, ' ').trim()).filter(Boolean);
}

function hasStructuredSignal(text) {
  if (!text) return false;

  const bulletPattern = /(^|\n)\s*([\-•*]|\d+\.)\s+\S+/m;
  const headingPattern = /(^|\n)\s*(핵심|요약|정리|포인트|근거|리스크|액션)\s*[:：]/m;
  const markdownHeadingPattern = /(^|\n)\s*#{2,4}\s+\S+/m;

  return bulletPattern.test(text) || headingPattern.test(text) || markdownHeadingPattern.test(text);
}

function buildTitle(mode, contextPayload, userPrompt) {
  if (mode === 'stock' && contextPayload?.stock_name) {
    return `${contextPayload.stock_name} 캔버스`;
  }

  if (userPrompt && userPrompt.length <= 28) {
    return userPrompt;
  }

  if (mode === 'education') return '학습 캔버스';
  if (mode === 'home') return '오늘 시장 흐름';

  return '에이전트 캔버스';
}

function buildActions(mode) {
  if (mode === 'stock') {
    return ['내 포트폴리오 영향은?', '리스크 포인트만 추려줘'];
  }

  if (mode === 'education') {
    return ['핵심 개념만 복습하기', '이걸 투자에 연결해줘'];
  }

  return ['모의투자에 반영하기', '과거 비슷한 사례 보기'];
}

function normalizeUiActions(uiActions) {
  if (!Array.isArray(uiActions)) return [];

  return uiActions
    .map((action, index) => {
      if (!action) return null;
      if (typeof action === 'string') {
        return {
          id: `action-${index}`,
          label: action,
          prompt: action,
        };
      }

      const label = action.label || action.title || action.text || action.prompt;
      if (!label) return null;

      return {
        id: action.id || `action-${index}`,
        label,
        prompt: action.prompt || label,
      };
    })
    .filter(Boolean);
}

function buildModeLabel(mode) {
  if (mode === 'stock') return '종목 컨텍스트';
  if (mode === 'education') return '학습 컨텍스트';
  if (mode === 'my') return 'MY 컨텍스트';
  return '홈 컨텍스트';
}

function normalizeSources(sources) {
  if (!Array.isArray(sources)) return [];

  return sources
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      title: String(item.title || item.content || '출처').trim(),
      url: String(item.url || '').trim(),
      source_kind: String(item.source_kind || item.type || 'internal').trim(),
      is_reachable: item.is_reachable === null || item.is_reachable === undefined
        ? null
        : Boolean(item.is_reachable),
      metrics: item.metrics && typeof item.metrics === 'object' ? item.metrics : null,
    }));
}

function collectMetricRows(sources) {
  const labelMap = {
    revenue: '매출액',
    operating_income: '영업이익',
    net_income: '당기순이익',
    total_assets: '자산총계',
    total_liabilities: '부채총계',
  };

  for (const source of sources) {
    if (!source?.metrics) continue;
    const rows = Object.entries(source.metrics)
      .filter(([key, value]) => labelMap[key] && Number.isFinite(Number(value)))
      .map(([key, value]) => ({
        key,
        label: labelMap[key],
        value: Number(value),
      }));

    if (rows.length > 0) {
      return rows;
    }
  }

  return [];
}

export default function composeCanvasState({
  messages,
  mode = 'home',
  contextPayload = null,
  aiStatus = null,
  userPrompt = '',
  assistantText: assistantTextOverride = '',
  assistantTurn = null,
}) {
  const assistantText = (assistantTextOverride || pickAssistantText(messages) || '').trim();
  const structured = assistantTurn?.structured && typeof assistantTurn.structured === 'object'
    ? assistantTurn.structured
    : null;
  const paragraphs = splitParagraphs(assistantText);
  const sentences = splitSentences(assistantText);
  const hasStructuredMarkdown = hasStructuredSignal(assistantText);
  const normalizedUiActions = normalizeUiActions(assistantTurn?.uiActions);
  const normalizedSources = normalizeSources(assistantTurn?.sources);
  const metricRows = collectMetricRows(normalizedSources);
  const fallbackActions = buildActions(mode).map((action, index) => ({
    id: `fallback-${index}`,
    label: action,
    prompt: action,
  }));

  const structuredActions = Array.isArray(structured?.suggested_actions)
    ? structured.suggested_actions
      .map((item, index) => ({
        id: `structured-action-${index}`,
        label: String(item || '').trim(),
        prompt: String(item || '').trim(),
      }))
      .filter((item) => item.label)
    : [];

  const keyPoint = structured?.summary || sentences[0] || paragraphs[0] || '';
  const explanation = sentences.slice(1, 3).join(' ') || paragraphs[1] || '';
  const bullets = hasStructuredMarkdown ? extractBullets(assistantText, sentences) : [];
  const quote = hasStructuredMarkdown ? (sentences[sentences.length - 1] || '') : '';

  return {
    title: buildTitle(mode, contextPayload, userPrompt),
    modeLabel: buildModeLabel(mode),
    viewType: assistantText ? (structured || hasStructuredMarkdown ? 'structured' : 'plain') : 'empty',
    keyPoint,
    explanation,
    bullets,
    quote,
    textBlocks: paragraphs.length > 0 ? paragraphs : (assistantText ? [assistantText] : []),
    actions: normalizedUiActions.length > 0
      ? normalizedUiActions
      : (structuredActions.length > 0 ? structuredActions : fallbackActions),
    aiStatus: aiStatus || '대기 중',
    userPrompt,
    structured,
    rawAssistantText: assistantText,
    sources: normalizedSources,
    metricRows,
  };
}
