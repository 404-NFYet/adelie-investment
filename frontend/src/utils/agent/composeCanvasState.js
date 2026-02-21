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

function buildTitle(mode, contextPayload, firstSentence) {
  if (mode === 'stock' && contextPayload?.stock_name) {
    return `${contextPayload.stock_name} 체크포인트`; 
  }

  if (firstSentence && firstSentence.length <= 40) {
    return firstSentence;
  }

  return '오늘 이슈 핵심 정리';
}

function buildActions(mode) {
  if (mode === 'stock') {
    return ['내 포트폴리오 영향은?', '과거 비슷한 사례 보기'];
  }

  return ['모의투자에 반영하기', '과거 비슷한 사례 보기'];
}

export default function composeCanvasState({
  messages,
  mode = 'home',
  contextPayload = null,
  aiStatus = null,
  userPrompt = '',
}) {
  const assistantText = pickAssistantText(messages);
  const sentences = splitSentences(assistantText);

  const keyPoint = sentences[0] || '핵심 요약을 만드는 중입니다.';
  const explanation = sentences.slice(1, 3).join(' ') || '질문 맥락에 맞춘 설명을 준비하고 있습니다.';
  const bullets = extractBullets(assistantText, sentences);
  const quote = sentences[sentences.length - 1] || keyPoint;

  return {
    title: buildTitle(mode, contextPayload, sentences[0]),
    modeLabel: mode === 'stock' ? '종목 튜터' : '아델리 브리핑',
    keyPoint,
    explanation,
    bullets,
    quote,
    actions: buildActions(mode),
    aiStatus: aiStatus || '응답 대기 중',
    userPrompt,
    rawAssistantText: assistantText,
  };
}
