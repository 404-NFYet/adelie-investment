const SESSION_META_PREFIX = 'session_meta:';

function toMetaKey(sessionId) {
  if (!sessionId) return '';
  return `${SESSION_META_PREFIX}${sessionId}`;
}

function safeJsonParse(raw) {
  if (!raw || typeof raw !== 'string') return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function dedupeKeywords(values) {
  const picked = [];
  const seen = new Set();

  for (const value of values || []) {
    const normalized = String(value || '').trim();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    picked.push(normalized);
    if (picked.length >= 5) break;
  }

  return picked;
}

export function readSessionCardMeta(sessionId) {
  const key = toMetaKey(sessionId);
  if (!key) return null;

  try {
    return safeJsonParse(localStorage.getItem(key));
  } catch {
    return null;
  }
}

export function writeSessionCardMeta(sessionId, nextMeta) {
  const key = toMetaKey(sessionId);
  if (!key || !nextMeta || typeof nextMeta !== 'object') return null;

  const previous = readSessionCardMeta(sessionId) || {};
  const merged = {
    ...previous,
    ...nextMeta,
    keywords: dedupeKeywords(nextMeta.keywords || previous.keywords || []),
    updated_at: new Date().toISOString(),
  };

  try {
    localStorage.setItem(key, JSON.stringify(merged));
  } catch {
    return previous;
  }

  return merged;
}

function collectKeywordObjects(contextPayload) {
  const context = contextPayload?.context || contextPayload || {};
  const keywords = Array.isArray(context?.keywords)
    ? context.keywords
    : Array.isArray(context?.ui_snapshot?.keywords)
      ? context.ui_snapshot.keywords
      : [];

  return keywords.filter(Boolean);
}

function getKeywordLabels(keywordObjects) {
  return keywordObjects
    .map((item) => (
      item?.title
      || item?.keyword
      || item?.name
      || item?.label
      || ''
    ))
    .filter(Boolean);
}

function getContextPayload(contextInfo) {
  const raw = contextInfo?.stepContent;
  if (!raw || typeof raw !== 'string') return null;
  return safeJsonParse(raw);
}

export function buildSessionCardMeta({
  contextInfo,
  fallbackTitle = '',
  fallbackSnippet = '',
  fallbackIconKey = null,
} = {}) {
  const payload = getContextPayload(contextInfo);
  const keywordObjects = collectKeywordObjects(payload);
  const keywordLabels = dedupeKeywords(getKeywordLabels(keywordObjects));

  const firstKeyword = keywordObjects[0] || null;
  const context = payload?.context || payload || {};

  const iconKey = (
    firstKeyword?.icon_key
    || context?.icon_key
    || fallbackIconKey
    || null
  );

  const title = (
    firstKeyword?.title
    || context?.case_title
    || context?.stock_name
    || fallbackTitle
    || ''
  );

  return {
    title,
    snippet: fallbackSnippet,
    icon_key: iconKey,
    keywords: keywordLabels,
  };
}
