/**
 * Narrative.jsx - 콘텐츠1~6 스타일 기반 내러티브 화면
 * 순서: background -> concept_explain -> history -> application -> caution -> summary
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { learningApi, narrativeApi } from '../api';
import { usePortfolio } from '../contexts/PortfolioContext';
import { useTermContext } from '../contexts/TermContext';
import { useTutor } from '../contexts';
import { useUser } from '../contexts/UserContext';
import { buildNarrativePlot } from '../utils/narrativeChartAdapter';
import ResponsiveEChart from '../components/charts/ResponsiveEChart';
import ResponsivePlotly from '../components/charts/ResponsivePlotly';
import { convertPlotlyToECharts } from '../utils/charts/plotlyToEcharts';
import RewardResultScreen from '../components/narrative/RewardResultScreen';
import { trackEvent } from '../utils/analytics';

const STEP_CONFIGS = [
  {
    key: 'background',
    tag: '#현재 배경',
    title: '지금 왜 이 이슈가 중요한가요?',
    template: 'content1',
    showChart: true,
  },
  {
    key: 'concept_explain',
    tag: '#핵심 개념',
    title: '핵심 금융 개념을 쉽게 풀어볼게요',
    template: 'content2',
    showChart: true,
  },
  {
    key: 'history',
    tag: '#과거 사례',
    title: '과거에도 비슷한 일이 있었을까요?',
    template: 'content3',
    showChart: true,
  },
  {
    key: 'application',
    tag: '#현재 적용',
    title: '그럼 지금 시장은 어떻게 봐야 할까요?',
    template: 'content3',
    showChart: true,
  },
  {
    key: 'caution',
    tag: '#주의 사항',
    title: '투자 전에 꼭 확인할 포인트',
    template: 'content4',
    showChart: false,
  },
  {
    key: 'summary',
    tag: '#최종 정리',
    title: '핵심만 짧게 정리합니다',
    template: 'content5',
    showChart: false,
  },
];

const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 110 : -110,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction) => ({
    x: direction > 0 ? -110 : 110,
    opacity: 0,
  }),
};

const SWIPE_THRESHOLD = 70;
const SWIPE_VELOCITY = 420;
const RESUME_STORAGE_PREFIX = 'adelie:narrative:resume:';
const RESUME_TTL_MS = 24 * 60 * 60 * 1000;
const CTA_GUARD_SELECTOR = '#tutor-selection-btn, #narrative-selection-cta';
const SELECTION_IGNORE_SELECTOR = '#tutor-selection-btn, button, [role="button"], nav, input, textarea, select, option';

const getResumeStorageKey = (caseId) => `${RESUME_STORAGE_PREFIX}${caseId}`;

function getPlainLines(content) {
  if (!content) return [];
  return content
    .replace(/<[^>]+>/g, ' ')
    .split('\n')
    .map((line) => line.replace(/^#{1,6}\s*/, '').replace(/^[-*]\s*/, '').trim())
    .filter(Boolean);
}

function sanitizeChecklistItem(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeChecklistLabelStyle(value) {
  const text = String(value || '').trim();
  if (!text) return text;

  const splitIdx = text.search(/[:：]/);
  if (splitIdx <= 0) return text;

  const rawLabel = text.slice(0, splitIdx).trim();
  const body = text.slice(splitIdx + 1).trim();
  if (!rawLabel || !body) return text;

  // 라벨은 동사형 종결보다 명사형 어구로 정리한다. (예: "대비해" -> "대비")
  const nounLikeLabel = rawLabel
    .replace(/\s+/g, ' ')
    .replace(/(하세요|해요|하라|하기|해)\s*$/u, '')
    .trim();

  const label = nounLikeLabel || rawLabel;
  return `${label}: ${body}`;
}

function normalizeDupKey(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\[(?:Trigger|Process|시차\/Variables|Result|Outcome)\]\s*/gi, '')
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .replace(/[^0-9a-zA-Z가-힣]+/g, '')
    .trim();
}

function isNearDuplicateSentence(sentence, referenceKeys) {
  const key = normalizeDupKey(sentence);
  if (!key || key.length < 18) return false;
  for (const ref of referenceKeys) {
    if (!ref || ref.length < 18) continue;
    if (key === ref || key.includes(ref) || ref.includes(key)) {
      return true;
    }
  }
  return false;
}

function dedupeConceptExplainContent(content, concept) {
  const text = String(content || '').trim();
  if (!text) return text;
  if (!concept || typeof concept !== 'object') return text;

  const conceptName = String(concept.name || '').trim();
  const likelyIntroHeading = (line) => /^#{1,6}\s*(?:🔹\s*)?개념\s*먼저\s*잡기\s*$/i.test(line.trim());
  const likelyIntroLine = (line) => /오늘\s+알아볼\s+개념은?\s+/i.test(line);
  const likelyDefinitionLine = (line) => (
    !!conceptName
    && line.includes(conceptName)
    && /(란\?|쉽게\s*말해|현상이|상태이|의미해요?)/.test(line)
  );

  const normalizedPhrases = [concept.definition, concept.relevance]
    .map((v) => String(v || '').trim())
    .filter(Boolean)
    .flatMap((v) => v.split(/[.!?。！？\n]/))
    .map((v) => normalizeDupKey(v))
    .filter((v) => v.length >= 14);

  const referenceKeys = [
    normalizeDupKey(conceptName),
    normalizeDupKey(concept.definition),
    normalizeDupKey(concept.relevance),
    ...normalizedPhrases,
  ].filter(Boolean);
  if (referenceKeys.length === 0) return text;

  const lines = text.split('\n');
  const deduped = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed) return line;
    if (likelyIntroHeading(trimmed)) return '';
    if (/^#{1,6}\s+/.test(trimmed)) return line;
    if (likelyIntroLine(trimmed) || likelyDefinitionLine(trimmed)) return '';

    const sentences = trimmed.match(/[^.!?。！？]+[.!?。！？]?/g) || [trimmed];
    const kept = sentences
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((s) => !likelyIntroLine(s) && !likelyDefinitionLine(s))
      .filter((s) => !isNearDuplicateSentence(s, referenceKeys));
    return kept.join(' ').trim();
  }).filter(Boolean);

  // 모든 줄이 날아가면 의미 손실이 커서 원문 유지
  return deduped.length > 0 ? deduped.join('\n') : text;
}

function getChecklistItems(content, bullets) {
  const items = [];
  const pushItem = (value) => {
    const cleaned = normalizeChecklistLabelStyle(sanitizeChecklistItem(value));
    if (!cleaned) return;
    if (/투자 전에 꼭 확인할 포인트/.test(cleaned)) return;
    if (!items.includes(cleaned)) {
      items.push(cleaned);
    }
  };

  if (Array.isArray(bullets)) {
    bullets.forEach(pushItem);
  }

  String(content || '')
    .split('\n')
    .forEach((line) => {
      const match = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.+)$/);
      if (match?.[1]) {
        pushItem(match[1]);
      }
    });

  return items.slice(0, 5);
}

// CommonMark delimiter 규칙 우회: 한글+스마트인용부호 환경에서 **bold** 렌더링 보장
function preprocessMarkdown(content) {
  if (!content) return '';
  let s = content;

  // 1) *[text] 패턴 제거 (LLM 오류: orphan * — *[유사점]** 같은 패턴)
  s = s.replace(/\*(\[[^\]]+\])/g, '$1');

  // 2) [text]** 패턴에서 ** 제거 (bracket 닫힘 직후 ** — 잘못된 delimiter)
  s = s.replace(/(\[[^\]]+\])\*\*/g, '$1');

  // 3) *텍스트** → **텍스트** 정규화 (앞 * 하나·뒤 ** 두 개 비대칭 LLM 오류)
  s = s.replace(/(?<!\*)\*(?!\*)((?:[^*\n])+?)\*\*/g, '**$1**');

  // 4) **...** → <strong>...</strong>
  //    right-flanking delimiter 실패 케이스 (punctuation + ** + 한글 / HTML 태그) 포함
  s = s.replace(/\*\*((?:(?!\*\*)[^\n])+?)\*\*/g, '<strong>$1</strong>');

  // 5) 잔여 ** 정리 (매칭 실패한 고립 opening/closing delimiter)
  s = s.replace(/\*\*/g, '');

  // 5-1) 줄긋기 마크다운/HTML(del,s,strike)은 모두 제거한다.
  s = s.replace(/~~/g, '');
  s = s.replace(/<\/?(?:del|s|strike)\b[^>]*>/gi, '');

  // 6) 내러티브 핵심 라벨 표기를 공통 포맷으로 통일한다.
  s = normalizeNarrativeBracketTags(s);

  // 7) "이번에 주는 힌트"가 위 사례와 동일하면 힌트 문구를 압축해 중복을 줄인다.
  s = normalizeHintDedup(s);

  // 8) "라벨: 설명" 구조는 문장 단위로 줄바꿈해 가독성을 맞춘다.
  s = normalizeLabelDescriptionBreaks(s);

  // 8) "[Trigger]" 같은 라벨은 문장과 분리해 줄바꿈해 가독성을 높인다.
  s = normalizeHistoricalLabelBreaks(s);

  return s;
}

function normalizeLabelDescriptionBreaks(content) {
  const text = String(content || '');
  if (!text) return text;

  // "문장 끝 + 다음 라벨: 설명" 패턴을 전역으로 정리한다.
  // 예) "...했어요. ETF 투자자 주의: ..." -> "...했어요.\nETF 투자자 주의: ..."
  return text.replace(
    /(?<!\d)([.!?。！？])\s+(\*\*)?([가-힣A-Za-z0-9·()/~\-\s]{2,40}:)(\*\*)?\s*/g,
    (_, endPunc, openBold = '', label, closeBold = '') => `${endPunc}\n${openBold}${label}${closeBold} `,
  );
}

function normalizeNarrativeBracketTags(content) {
  const text = String(content || '');
  if (!text) return text;

  let out = text;

  // [원인 Trigger], [Trigger 원인], [원인(Trigger)], [Trigger(원인)], [원인], [Trigger] -> [Trigger]
  out = out.replace(
    /\[\s*(?:원인\s*[-/|]?\s*trigger|trigger\s*[-/|]?\s*원인|원인\s*\(\s*trigger\s*\)|trigger\s*\(\s*원인\s*\)|원인|trigger)\s*\]/gi,
    '[Trigger]',
  );
  // 원인(Trigger):, Trigger(원인): -> [Trigger]
  out = out.replace(/(^|[\s>])(?:원인\s*\(\s*trigger\s*\)|trigger\s*\(\s*원인\s*\))\s*:\s*/gim, '$1[Trigger] ');

  // [전개 Process], [Process 전개], [전개(Process)], [Process(전개)], [전개], [Process] -> [Process]
  out = out.replace(
    /\[\s*(?:전개\s*[-/|]?\s*process|process\s*[-/|]?\s*전개|전개\s*\(\s*process\s*\)|process\s*\(\s*전개\s*\)|전개|process)\s*\]/gi,
    '[Process]',
  );
  // 전개(Process):, Process(전개): -> [Process]
  out = out.replace(/(^|[\s>])(?:전개\s*\(\s*process\s*\)|process\s*\(\s*전개\s*\))\s*:\s*/gim, '$1[Process] ');

  // [시차/변수], [Time Lag/Variables], [Variables], [시차/Variables] -> [시차/Variables]
  out = out.replace(/\[\s*(?:시차\s*\/\s*변수|시차\s*\/\s*variables|time\s*lag\s*\/\s*variables|variables)\s*\]/gi, '[시차/Variables]');
  // 시차/변수(시차/Variables):, Time Lag/Variables: -> [시차/Variables]
  out = out.replace(
    /(^|[\s>])(?:시차\s*\/\s*변수(?:\s*\(\s*시차\s*\/\s*variables\s*\))?|time\s*lag\s*\/\s*variables|variables)\s*:\s*/gim,
    '$1[시차/Variables] ',
  );

  return out;
}

function buildHintFromWholeContext(sourceText) {
  const raw = String(sourceText || '')
    .replace(/^###\s+.*$/gm, ' ')
    .replace(/\[(?:Trigger|Process|시차\/Variables|Result|Outcome)\]\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim();

  const factors = [];
  if (/정책|규제|발표|정부/.test(raw)) factors.push('정책');
  if (/수급|자금|매수|매도|유입/.test(raw)) factors.push('수급');
  if (/실적|이익|매출|밸류|멀티플/.test(raw)) factors.push('실적/밸류');
  if (/금리|유동성|거시|환율|물가/.test(raw)) factors.push('거시 환경');
  if (/시차|lag|타이밍|선행|후행/.test(raw)) factors.push('시차');
  if (/리스크|변동성|과열|조정/.test(raw)) factors.push('리스크');

  const uniqueFactors = Array.from(new Set(factors));
  const factorText = uniqueFactors.slice(0, 3).join('·') || '수급·심리·타이밍';
  const hasLag = /시차|lag|선행|후행|타이밍/.test(raw);
  const hasTheme = /테마|동조화|섹터|대장주/.test(raw);

  const line1 = hasTheme
    ? `핵심 힌트: 이번 구간은 개별 뉴스보다 ${factorText}의 방향이 주가를 먼저 움직일 가능성이 큽니다.`
    : `핵심 힌트: 이번 구간에서는 ${factorText}의 변화가 단기 주가 반응을 좌우할 가능성이 큽니다.`;

  const line2 = hasLag
    ? '체크 포인트: 같은 재료라도 반응 시차가 생기므로 진입·추가·정리 타이밍을 한 번에 판단하지 말고 나눠 확인하세요.'
    : '체크 포인트: 강한 재료가 보여도 확산 경로와 지속성을 먼저 확인한 뒤 대응하면 오판 가능성을 줄일 수 있습니다.';

  return [line1, line2];
}

function normalizeHintDedup(content) {
  const text = String(content || '');
  if (!text.includes('### 이번에 주는 힌트')) return text;

  const lines = text.split('\n');
  const hintStart = lines.findIndex((line) => /^###\s*이번에 주는 힌트/.test(line.trim()));
  if (hintStart < 0) return text;
  const hintEnd = lines.findIndex((line, idx) => idx > hintStart && /^###\s+/.test(line.trim()));
  const hintSliceEnd = hintEnd === -1 ? lines.length : hintEnd;
  const sourceContext = [
    ...lines.slice(0, hintStart),
    ...lines.slice(hintSliceEnd),
  ].join('\n');
  const compactLines = buildHintFromWholeContext(sourceContext);

  return [
    ...lines.slice(0, hintStart + 1),
    ...compactLines,
    ...lines.slice(hintSliceEnd),
  ].join('\n');
}

function normalizeHistoricalLabelBreaks(content) {
  const text = String(content || '');
  if (!text) return text;
  const labelPattern = '\\[(?:Trigger|Process|Result|Outcome|Time\\s*Lag\\/Variables|Variables|시차\\/Variables)\\]';
  let out = text;

  // "국면: [Trigger]" 같은 패턴은 ":" 다음 줄로 라벨을 내린다.
  out = out.replace(new RegExp(`([:：])\\s*(${labelPattern})`, 'g'), '$1\n$2');
  // 일반 문장 중간에 붙은 라벨도 새 줄에서 시작하게 정리한다.
  out = out.replace(new RegExp(`([^\\n:：])\\s+(${labelPattern})`, 'g'), '$1\n$2');

  return out;
}

function pickSubheadingEmoji(text) {
  const t = String(text || '').toLowerCase();
  if (/과거|history|사례/.test(t)) return '🕰️';
  if (/힌트|tip|포인트|check|체크/.test(t)) return '💡';
  if (/리스크|위험|주의|caution/.test(t)) return '⚠️';
  if (/기회|호재|상승|긍정|opportunity/.test(t)) return '🚀';
  if (/전략|액션|대응|strategy|plan/.test(t)) return '🧭';
  if (/데이터|지표|숫자|차트|data|metric/.test(t)) return '📊';
  if (/요약|핵심|summary|takeaway/.test(t)) return '🧩';
  return '🔹';
}

function resolveSubheadingTone(text, defaultColorClass) {
  const emoji = pickSubheadingEmoji(text);
  const colorClass = emoji === '🔹' ? 'text-[#1e3a8a]' : defaultColorClass;
  return { emoji, colorClass };
}

function renderSubheadingWithEmoji(props) {
  const raw = props.children;
  const headingText = Array.isArray(raw) ? raw.join(' ') : String(raw || '');
  const { emoji } = resolveSubheadingTone(headingText, 'text-primary');
  return (
    <>
      <span aria-hidden="true" className="mr-1.5">{emoji}</span>
      {props.children}
    </>
  );
}

function normalizeCautionActionPoints(content) {
  const text = String(content || '');
  if (!text) return text;

  const lines = text.split('\n');
  const out = [];
  let inAction = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      inAction = trimmed.includes('대응 포인트');
      out.push(line);
      continue;
    }

    if (!inAction) {
      out.push(line);
      continue;
    }

    if (!trimmed) {
      out.push(line);
      inAction = false;
      continue;
    }

    // "문장 끝 + 다음 라벨: 설명" 패턴을 강제로 줄바꿈한다.
    // 라벨이 **굵게** 감싸진 마크다운 케이스도 함께 처리한다.
    const normalized = trimmed.replace(
      /([.!?。！？])\s+(\*\*)?([가-힣A-Za-z0-9·()/\-\s]{2,40}:)(\*\*)?\s*/g,
      (_, endPunc, openBold = '', label, closeBold = '') => `${endPunc}\n${openBold}${label}${closeBold} `,
    );
    out.push(normalized);
  }

  return out.join('\n');
}

function toActionableCautionLine(item, idx) {
  const cleaned = sanitizeChecklistItem(item);
  const base = cleaned.replace(/[:：].*$/g, '').replace(/\s+/g, ' ').trim();
  const fallbackTopics = ['비중 관리 원칙', '분할 대응 원칙', '유동성 점검 원칙'];
  const topic = (() => {
    if (/시차|전환|기대.?현실|갭|후행|선행/.test(base)) return '기대-현실 갭 대응';
    if (/etf|nav|유동성|괴리|편입/.test(base.toLowerCase())) return 'ETF 유동성 점검';
    if (/과열|경고|이벤트|급등|변동성/.test(base)) return '이벤트 과열 경계';
    if (/실적|매출|영업이익|밸류|멀티플/.test(base)) return '실적 확인 우선';
    if (/분산|집중|비중/.test(base)) return '비중 관리';
    return fallbackTopics[idx % fallbackTopics.length];
  })();

  const templates = [
    `${topic}: 진입 전에 확인 지표 1개와 중단 조건 1개를 먼저 정하세요. 조건이 충족되기 전에는 비중을 늘리지 않습니다.`,
    `${topic}: 이벤트 직후에는 2~3회 분할로 대응하고, 반대 시그널이 나오면 즉시 비중을 줄이세요.`,
    `${topic}: 단일 종목 대신 관련 ETF·대체 종목을 함께 비교해 분산하고, 거래대금/괴리율을 같이 확인하세요.`,
  ];

  return templates[idx % templates.length];
}

function buildCautionActionGuide(content, bullets = []) {
  const normalized = normalizeCautionActionPoints(content);
  const lines = String(normalized || '').split('\n');
  const actionHeadingIdx = lines.findIndex((line) => line.trim().includes('대응 포인트'));
  const intro = (actionHeadingIdx >= 0 ? lines.slice(0, actionHeadingIdx) : lines).join('\n').trim();

  const sourceItems = (Array.isArray(bullets) ? bullets : [])
    .map((v) => sanitizeChecklistItem(v))
    .filter(Boolean)
    .slice(0, 3);

  const actionable = (sourceItems.length > 0
    ? sourceItems.map((item, idx) => toActionableCautionLine(item, idx))
    : [
      '핵심 리스크: 진입 전에 확인 지표와 중단 조건을 먼저 정해 추격 매수를 피하세요.',
      '체크 포인트: 이벤트 당일 변동성보다 다음 영업일의 거래대금·수급 지속 여부를 우선 확인하세요.',
    ]);

  const actionSection = [
    '### 대응 포인트',
    ...actionable.map((line, idx) => `${idx + 1}. ${line}`),
  ].join('\n');

  return [intro, actionSection].filter(Boolean).join('\n\n');
}

function normalizeApplicationSection(content) {
  const text = String(content || '');
  if (!text) return text;
  if (!text.includes('### 닮은 점') || !text.includes('### 다른 점')) return text;

  const lines = text.split('\n');
  const top = [];
  const similar = [];
  const different = [];
  let similarHeading = null;
  let differentHeading = null;
  let section = 'top';
  const isSimilarityLine = (rawLine) => {
    const normalized = String(rawLine || '')
      .trim()
      .replace(/^[-*]\s*/, '')
      .replace(/^\*\*|\*\*$/g, '');
    return /^\[?\s*유사점(?:\s*[-—:])?/i.test(normalized)
      || /^닮은\s*점(?:\s*\(패턴\))?\s*:/.test(normalized)
      || /\[유사점\s*[-—:]/.test(normalized);
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      if (trimmed.includes('닮은 점')) {
        similarHeading = line;
        section = 'similar';
        continue;
      }
      if (trimmed.includes('다른 점')) {
        differentHeading = line;
        section = 'different';
        continue;
      }
    }

    if (section === 'top') {
      top.push(line);
      continue;
    }
    if (section === 'similar') {
      similar.push(line);
      continue;
    }

    // "다른 점" 섹션에 잘못 들어간 유사점/닮은점 라인은 "닮은 점"으로 이동.
    if (isSimilarityLine(trimmed)) {
      similar.push(line);
    } else {
      different.push(line);
    }
  }

  const output = [];
  output.push(...top);
  if (similarHeading) output.push(similarHeading, ...similar);
  if (differentHeading) output.push(differentHeading, ...different);
  return output.join('\n');
}

function normalizeLessonLineBreaks(content) {
  const text = String(content || '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return text;

  // 문장 종결 뒤에는 줄바꿈해 가독성을 높인다.
  return text.replace(/([.!?。！？])\s+/g, '$1\n');
}

const MarkdownBody = React.memo(function MarkdownBody({ content, className = '', headingColorClass = 'text-primary' }) {
  if (!content) return null;
  const processed = preprocessMarkdown(content);

  return (
    <div className={`${className} select-text`} style={{ userSelect: 'text', WebkitUserSelect: 'text' }}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm, remarkBreaks]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        components={{
          mark: ({ node, ...props }) => <span className="term-highlight" data-term-highlight="true" {...props} />,
          h1: ({ node, ...props }) => <h3 className={`mb-2 text-base font-semibold ${headingColorClass}`} {...props} />,
          h2: ({ node, ...props }) => (
            <h3
              {...props}
              className={`mb-2 text-base font-semibold ${
                resolveSubheadingTone(props.children, headingColorClass).colorClass
              }`}
            >
              {renderSubheadingWithEmoji(props)}
            </h3>
          ),
          h3: ({ node, ...props }) => (
            <h4
              {...props}
              className={`mb-2 text-sm font-semibold ${
                resolveSubheadingTone(props.children, headingColorClass).colorClass
              }`}
            >
              {renderSubheadingWithEmoji(props)}
            </h4>
          ),
          p: ({ node, ...props }) => <p className="mb-3 whitespace-pre-line text-sm leading-relaxed text-text-secondary last:mb-0" {...props} />,
          ul: ({ node, ...props }) => <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-text-secondary" {...props} />,
          ol: ({ node, ...props }) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-text-secondary" {...props} />,
          li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
          blockquote: ({ node, ...props }) => (
            <blockquote className="my-3 border-l-[3px] border-primary/40 bg-[#fff8f3] py-2 pl-4 pr-3 text-[13px] leading-relaxed text-text-secondary" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-text-primary" {...props} />
          ),
          del: ({ node, ...props }) => <span {...props} />,
          table: ({ node, ...props }) => (
            <div className="my-3 overflow-x-auto"><table className="w-full text-xs" {...props} /></div>
          ),
          thead: ({ node, ...props }) => <thead className="border-b border-border bg-gray-50" {...props} />,
          td: ({ node, ...props }) => <td className="px-2 py-1.5 text-text-secondary" {...props} />,
          th: ({ node, ...props }) => <th className="px-2 py-1.5 text-left font-semibold text-text-primary" {...props} />,
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
});

function NarrativeChartBlock({ stepKey, chart }) {
  const plot = useMemo(() => buildNarrativePlot(stepKey, chart), [stepKey, chart]);
  const chartRatio = stepKey === 'background' ? 1.38 : 1.16;
  const converted = useMemo(
    () => (plot.hasRenderable ? convertPlotlyToECharts(plot.data, plot.layout) : { convertible: false }),
    [plot.data, plot.layout, plot.hasRenderable],
  );

  if (!plot.hasRenderable) {
    return null;
  }

  return (
    <section className="w-full">
      {plot.title ? <h4 className="mb-2 text-xs font-semibold text-text-secondary">{plot.title}</h4> : null}
      {plot.annotation ? <p className="mb-2 text-[11px] text-text-muted">{plot.annotation}</p> : null}

      {converted.convertible ? (
        <ResponsiveEChart
          option={converted.option}
          mode="ratio"
          ratio={chartRatio}
          minHeight={220}
          maxHeight={460}
          loadingText="차트 로딩 중..."
          emptyText="차트를 표시할 수 없습니다"
        />
      ) : (
        <ResponsivePlotly
          data={plot.data}
          layout={plot.layout}
          mode="ratio"
          ratio={chartRatio}
          minHeight={220}
          maxHeight={460}
          loadingText="차트 로딩 중..."
          emptyText="차트를 표시할 수 없습니다"
        />
      )}
    </section>
  );
}

function NarrativeSources({ sources = [] }) {
  if (!Array.isArray(sources) || sources.length === 0) return null;

  return (
    <section className="rounded-2xl border border-border bg-surface-elevated p-4">
      <p className="mb-2 text-[11px] font-semibold tracking-wide text-text-secondary">출처</p>
      <div className="space-y-2">
        {sources.slice(0, 6).map((src, idx) => {
          const label = src?.name || src?.title || src?.url_domain || `출처 ${idx + 1}`;
          const href = src?.url;

          if (href) {
            return (
              <a
                key={`${label}-${idx}`}
                href={href}
                target="_blank"
                rel="noreferrer"
                className="block text-xs text-text-secondary transition hover:text-primary"
              >
                {idx + 1}. {label}
              </a>
            );
          }

          return (
            <p key={`${label}-${idx}`} className="text-xs text-text-secondary">
              {idx + 1}. {label}
            </p>
          );
        })}
      </div>
    </section>
  );
}

const ContentTemplate = React.memo(function ContentTemplate({ stepConfig, stepData, stepTitle, oneLiner, data }) {
  const markdownContent = useMemo(() => {
    if (stepData?.content?.trim()) {
      return stepData.content;
    }

    if (Array.isArray(stepData?.bullets) && stepData.bullets.length > 0) {
      return stepData.bullets.map((item) => `- ${item}`).join('\n');
    }

    return '';
  }, [stepData?.content, stepData?.bullets]);

  const contentLines = getPlainLines(stepData?.content || '');
  const cautionItems = (stepData?.bullets && stepData.bullets.length > 0)
    ? stepData.bullets
    : contentLines.slice(0, 5);
  const summaryChecklist = getChecklistItems(stepData?.content, stepData?.bullets);
  const cautionContent = stepConfig.template === 'content4'
    ? buildCautionActionGuide(stepData?.content, cautionItems)
    : stepData?.content;
  const applicationContent = stepConfig.key === 'application'
    ? normalizeApplicationSection(markdownContent)
    : markdownContent;
  const conceptContent = stepConfig.key === 'concept_explain'
    ? dedupeConceptExplainContent(markdownContent, data?.concept)
    : markdownContent;
  const hasHistoryBody = stepConfig.key === 'history' && Boolean(String(stepData?.content || '').trim());

  if (stepConfig.template === 'content4') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#eef2f6] px-3 py-1 text-[11px] font-semibold text-[#4b5563]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.45rem,5.6vw,2rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          {cautionItems.length > 0 ? (
            <ul className="mt-5 space-y-3">
              {cautionItems.slice(0, 5).map((item, idx) => (
                <li key={`${item}-${idx}`} className="rounded-xl bg-[#f7f8fa] px-4 py-3 text-sm leading-relaxed text-text-secondary">
                  <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-semibold text-primary">
                    {idx + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          ) : null}

          <MarkdownBody
            content={cautionContent}
            className={cautionItems.length > 0 ? 'mt-4 border-t border-border pt-4' : 'mt-5'}
          />
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content1') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#ffeede] px-3 py-1 text-[11px] font-semibold text-primary">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.75rem,7vw,2.55rem)] font-black leading-[1.15] tracking-[-0.02em] text-black">
            {stepTitle}
          </h2>
          {oneLiner ? (
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">{oneLiner}</p>
          ) : null}

          {data?.related_companies?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {data.related_companies.slice(0, 5).map((c, i) => (
                <span key={c.stock_code || i}
                  className="inline-flex items-center gap-1 rounded-full border border-[#e5e7eb] bg-white px-2.5 py-1 text-[11px] font-medium text-[#374151]">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  {c.stock_name}
                </span>
              ))}
            </div>
          )}

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}

          <MarkdownBody
            content={markdownContent}
            className="mt-5"
          />
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content2') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#e7eef7] px-3 py-1 text-[11px] font-semibold text-[#27507f]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          {data?.concept?.name && (
            <div className="mt-4 rounded-2xl border border-[#dbeafe] bg-[#eff6ff] p-4">
              <p className="text-[11px] font-semibold tracking-wide text-[#1e40af]">핵심 개념</p>
              <p className="mt-1 text-sm font-bold text-[#1e3a5f]">{data.concept.name}</p>
              <p className="mt-2 text-[13px] leading-relaxed text-[#374151]">{data.concept.definition}</p>
              {data.concept.relevance && (
                <p className="mt-2 text-[12px] leading-relaxed text-[#6b7280]">
                  <span className="font-semibold text-[#1e40af]">왜 중요한가: </span>{data.concept.relevance}
                </p>
              )}
            </div>
          )}

          <MarkdownBody
            content={conceptContent}
            className="mt-4"
            headingColorClass={stepConfig.key === 'history' ? 'text-[#065f46]' : 'text-primary'}
          />

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content3') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#eaf7ef] px-3 py-1 text-[11px] font-semibold text-[#1a7f54]">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.5rem,5.9vw,2.05rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          {stepConfig.key === 'history' && data?.historical_case?.title && (
            <div className="mt-4 rounded-2xl border border-[#d1fae5] bg-[#ecfdf5] p-4">
              <p className="text-[11px] font-semibold tracking-wide text-[#065f46]">과거 유사 사례</p>
              {data.historical_case.period && (
                <p className="mt-1.5 text-[11px] font-medium text-[#047857]">{data.historical_case.period}</p>
              )}
              <p className="mt-1 text-sm font-bold text-[#064e3b]">{data.historical_case.title}</p>
              {data.historical_case.summary && !hasHistoryBody && (
                <p className="mt-2 whitespace-pre-line text-[13px] leading-relaxed text-[#374151]">
                  {normalizeHistoricalLabelBreaks(data.historical_case.summary)}
                </p>
              )}
              {data.historical_case.outcome && !hasHistoryBody && (
                <div className="mt-2 rounded-xl bg-white/60 px-3 py-2">
                  <p className="text-[11px] font-semibold text-[#065f46]">결과</p>
                  <p className="mt-0.5 whitespace-pre-line text-[12px] leading-relaxed text-[#374151]">
                    {normalizeHistoricalLabelBreaks(data.historical_case.outcome)}
                  </p>
                </div>
              )}
              {hasHistoryBody && (
                <p className="mt-2 text-[12px] text-[#4b5563]">
                  상세 맥락은 아래 본문에서 확인하세요.
                </p>
              )}
            </div>
          )}

          <MarkdownBody
            content={applicationContent}
            className="mt-4"
            headingColorClass={stepConfig.key === 'history' ? 'text-[#065f46]' : 'text-primary'}
          />

          {stepConfig.showChart ? (
            <div className="mt-5">
              <NarrativeChartBlock stepKey={stepConfig.key} chart={stepData?.chart} />
            </div>
          ) : null}
        </div>
      </section>
    );
  }

  if (stepConfig.template === 'content5') {
    return (
      <section className="space-y-4">
        <div className="px-1 py-1">
          <span className="inline-flex rounded-full bg-[#fff0e1] px-3 py-1 text-[11px] font-semibold text-primary">
            {stepConfig.tag}
          </span>
          <h2 className="mt-3 text-[clamp(1.55rem,6vw,2.1rem)] font-extrabold leading-[1.2] text-black">
            {stepTitle}
          </h2>

          <h3 className="mt-4 text-sm font-semibold text-[#b45309]">투자 전에 꼭 확인할 포인트</h3>
          {summaryChecklist.length > 0 ? (
            <ul className="mt-2 space-y-2">
              {summaryChecklist.map((item, idx) => (
                <li key={`${item}-${idx}`} className="rounded-xl bg-[#fff7ed] px-4 py-3 text-sm leading-relaxed text-[#b45309]">
                  <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-semibold text-primary">
                    {idx + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          ) : null}

          {data?.historical_case?.lesson && (
            <div className="mt-4 flex items-start gap-2.5 rounded-2xl border border-[#ffedd5] bg-[#fff7ed] p-4">
              <span className="mt-0.5 text-base">💡</span>
              <div>
                <p className="text-[11px] font-semibold tracking-wide text-[#b45309]">과거에서 배우는 교훈</p>
                <p className="mt-1.5 whitespace-pre-line text-[13px] leading-relaxed text-[#92400e]">
                  {normalizeLessonLineBreaks(data.historical_case.lesson)}
                </p>
              </div>
            </div>
          )}

          {summaryChecklist.length === 0 ? (
            <MarkdownBody content={markdownContent} className="mt-4" />
          ) : null}
        </div>
      </section>
    );
  }

  return (
      <section className="px-2 py-3">
      <MarkdownBody content={markdownContent} />
    </section>
  );
});

export default function Narrative() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { claimReward } = usePortfolio();
  const { openTermSheet } = useTermContext();
  const {
    setContextInfo,
    updateSelectionCtaState,
    clearSelectionCtaState,
    selectionCtaState,
    askTutorFromSelection,
    isLoading: isTutorLoading,
  } = useTutor();
  const { settings } = useUser();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);

  const [rewardViewState, setRewardViewState] = useState('none');
  const [rewardData, setRewardData] = useState(null);
  const [rewardError, setRewardError] = useState('');
  const [pendingResumeState, setPendingResumeState] = useState(null);
  const [isResumeDialogOpen, setIsResumeDialogOpen] = useState(false);
  const [selectionPopupPos, setSelectionPopupPos] = useState({ x: 0, y: 0, placement: 'above' });

  const hasRestoredResumeRef = useRef(false);
  const scrollThrottleTimerRef = useRef(null);
  const hasLoggedInProgressRef = useRef(false);
  const selectionScopeRef = useRef(null);
  const swipeTouchRef = useRef(null);
  const lastSelectionTrackRef = useRef({ key: '', ts: 0 });
  const totalSteps = STEP_CONFIGS.length;

  // ──────────────────────────────────────────────
  // 튜터 컨텍스트 동기화
  // ──────────────────────────────────────────────
  useEffect(() => {
    if (!caseId) {
      setContextInfo(null);
      return;
    }

    const currentStepConfig = STEP_CONFIGS[currentStep];
    const currentStepData = data?.steps?.[currentStepConfig.key];
    let fullContextText = '';

    if (currentStepData) {
      const stepTitle = currentStepData.title || currentStepConfig.title;
      const stepContent = currentStepData.content || '';

      fullContextText = `[${stepTitle}]\n`;

      if (currentStepData.bullets && currentStepData.bullets.length > 0) {
        fullContextText += currentStepData.bullets.map((b) => `- ${b}`).join('\n') + '\n\n';
      }

      fullContextText += stepContent;
    }

    setContextInfo({
      type: 'case',
      id: Number(caseId),
      stepContent: fullContextText,
      stepKey: currentStepConfig.key,
      stepTitle: currentStepData?.title || currentStepConfig.title,
      stepTag: currentStepConfig.tag,
      sourcePage: 'narrative',
    });

    return () => setContextInfo(null);
  }, [caseId, data, currentStep, setContextInfo]);

  // ──────────────────────────────────────────────
  // 이어보기 (resume) 로직
  // ──────────────────────────────────────────────
  const clearResumeState = useCallback(() => {
    if (!caseId) return;
    try {
      localStorage.removeItem(getResumeStorageKey(caseId));
    } catch {
      // ignore localStorage errors
    }
  }, [caseId]);

  const saveResumeState = useCallback((stepIndex) => {
    if (!caseId) return;
    try {
      localStorage.setItem(
        getResumeStorageKey(caseId),
        JSON.stringify({
          stepIndex,
          scrollY: window.scrollY || 0,
          updatedAt: new Date().toISOString(),
        }),
      );
    } catch {
      // ignore localStorage errors
    }
  }, [caseId]);

  const readValidResumeState = useCallback(() => {
    if (!caseId) return null;
    try {
      const raw = localStorage.getItem(getResumeStorageKey(caseId));
      if (!raw) return null;

      const parsed = JSON.parse(raw);
      const savedAt = Date.parse(parsed?.updatedAt || '');
      if (!Number.isFinite(savedAt) || Date.now() - savedAt > RESUME_TTL_MS) {
        clearResumeState();
        return null;
      }

      const parsedStep = Number.isInteger(parsed?.stepIndex) ? parsed.stepIndex : 0;
      const safeStepIndex = Math.min(Math.max(parsedStep, 0), totalSteps - 1);
      const safeScrollY = Math.max(0, Number(parsed?.scrollY || 0));

      return {
        stepIndex: safeStepIndex,
        scrollY: safeScrollY,
      };
    } catch {
      clearResumeState();
      return null;
    }
  }, [caseId, clearResumeState, totalSteps]);

  const applyResumeState = useCallback((stepIndex, scrollY = 0) => {
    setDirection(0);
    setCurrentStep(stepIndex);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: scrollY, behavior: 'auto' });
      });
    });
  }, []);

  const upsertLearningProgress = useCallback(async (status, progressPercent) => {
    const parsedCaseId = Number(caseId);
    if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) return;

    try {
      await learningApi.upsertProgress({
        content_type: 'case',
        content_id: parsedCaseId,
        status,
        progress_percent: progressPercent,
      });
    } catch {
      // 학습 로그 실패는 화면 흐름을 막지 않음
    }
  }, [caseId]);

  useEffect(() => {
    hasRestoredResumeRef.current = false;
    hasLoggedInProgressRef.current = false;
    setRewardViewState('none');
    setRewardData(null);
    setRewardError('');
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setError('케이스 ID가 없습니다.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    narrativeApi.getNarrative(caseId)
      .then((response) => {
        if (!response || !response.steps) {
          throw new Error('내러티브 데이터가 없습니다.');
        }
        setData(response);
      })
      .catch((fetchError) => {
        setError(fetchError?.message || '내러티브 데이터를 불러오지 못했습니다.');
      })
      .finally(() => setIsLoading(false));
  }, [caseId]);

  const stepConfig = STEP_CONFIGS[currentStep];
  const stepData = data?.steps?.[stepConfig.key];
  const stepTitle = stepData?.title || stepConfig.title;
  const isLastStep = currentStep === totalSteps - 1;

  useEffect(() => {
    if (!caseId || !data || isLoading || error || hasLoggedInProgressRef.current) return;
    hasLoggedInProgressRef.current = true;
    upsertLearningProgress('in_progress', 20);
  }, [caseId, data, error, isLoading, upsertLearningProgress]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || hasRestoredResumeRef.current) return;

    let cancelled = false;

    const restoreEntry = async () => {
      const savedResume = readValidResumeState();

      if (!savedResume || savedResume.stepIndex <= 0) {
        hasRestoredResumeRef.current = true;
        applyResumeState(0, 0);
        return;
      }

      let isCompleted = false;
      try {
        const progressRes = await learningApi.getProgress({ contentType: 'case' });
        const progressList = Array.isArray(progressRes?.data) ? progressRes.data : [];
        const currentCaseProgress = progressList.find((item) => Number(item.content_id) === Number(caseId));
        isCompleted = currentCaseProgress?.status === 'completed';
      } catch {
        // 학습 진도 조회 실패 시 로컬 resume 기준으로 처리
      }

      if (cancelled) return;

      if (isCompleted) {
        clearResumeState();
        hasRestoredResumeRef.current = true;
        applyResumeState(0, 0);
        return;
      }

      setPendingResumeState(savedResume);
      setIsResumeDialogOpen(true);
    };

    restoreEntry();

    return () => {
      cancelled = true;
    };
  }, [applyResumeState, caseId, clearResumeState, data, error, isLoading, readValidResumeState]);

  const handleResumeFromBeginning = useCallback(() => {
    clearResumeState();
    hasRestoredResumeRef.current = true;
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
    applyResumeState(0, 0);
  }, [applyResumeState, clearResumeState]);

  const handleResumeFromSavedPoint = useCallback(() => {
    const stepIndex = pendingResumeState?.stepIndex || 0;
    const scrollY = pendingResumeState?.scrollY || 0;
    hasRestoredResumeRef.current = true;
    setPendingResumeState(null);
    setIsResumeDialogOpen(false);
    applyResumeState(stepIndex, scrollY);
  }, [applyResumeState, pendingResumeState]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || !hasRestoredResumeRef.current) return;
    saveResumeState(currentStep);
  }, [caseId, currentStep, data, error, isLoading, saveResumeState]);

  useEffect(() => {
    if (!caseId || !data || isLoading || error || !hasRestoredResumeRef.current) return undefined;

    const handleScroll = () => {
      if (scrollThrottleTimerRef.current) return;
      scrollThrottleTimerRef.current = window.setTimeout(() => {
        saveResumeState(currentStep);
        scrollThrottleTimerRef.current = null;
      }, 250);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollThrottleTimerRef.current) {
        window.clearTimeout(scrollThrottleTimerRef.current);
        scrollThrottleTimerRef.current = null;
      }
    };
  }, [caseId, currentStep, data, error, isLoading, saveResumeState]);

  // ──────────────────────────────────────────────
  // 단계 이동
  // ──────────────────────────────────────────────
  const goToStep = (nextIndex) => {
    if (nextIndex < 0 || nextIndex >= totalSteps) return;
    setDirection(nextIndex > currentStep ? 1 : -1);
    setCurrentStep(nextIndex);
  };

  const goPrev = () => {
    goToStep(currentStep - 1);
  };

  const goNext = async () => {
    if (!isLastStep) {
      goToStep(currentStep + 1);
      return;
    }

    try {
      setRewardError('');
      const reward = await claimReward(Number(caseId));
      if (reward) {
        setRewardData(reward);
        setRewardViewState('success');
        clearResumeState();
        upsertLearningProgress('completed', 100);
      }
    } catch (claimError) {
      const message = claimError?.message || '보상 청구에 실패했습니다.';
      if (message.includes('이미')) {
        setRewardData(null);
        setRewardViewState('already_claimed');
        clearResumeState();
        upsertLearningProgress('completed', 100);
        return;
      }
      setRewardError(message);
    }
  };

  // ──────────────────────────────────────────────
  // 스와이프 네비게이션 (순수 터치 이벤트)
  // ──────────────────────────────────────────────
  const handleSwipeTouchStart = useCallback((e) => {
    const touch = e.touches[0];
    if (!touch) return;
    swipeTouchRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
  }, []);

  const handleSwipeTouchEnd = useCallback((e) => {
    if (!swipeTouchRef.current) return;
    const touch = e.changedTouches[0];
    if (!touch) { swipeTouchRef.current = null; return; }

    const dx = touch.clientX - swipeTouchRef.current.x;
    const dy = touch.clientY - swipeTouchRef.current.y;
    const dt = Date.now() - swipeTouchRef.current.time;
    swipeTouchRef.current = null;

    // 세로 움직임이 더 크면 스크롤이므로 무시
    if (Math.abs(dy) > Math.abs(dx)) return;
    // 너무 느리면 스와이프가 아님
    if (dt > 500) return;
    // 텍스트 선택 중이면 스와이프 무시
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed && sel.toString().trim()) return;

    const velocity = (Math.abs(dx) / dt) * 1000;

    if (dx <= -SWIPE_THRESHOLD || velocity >= SWIPE_VELOCITY) {
      if (!isLastStep) goToStep(currentStep + 1);
    } else if (dx >= SWIPE_THRESHOLD || velocity >= SWIPE_VELOCITY) {
      goToStep(currentStep - 1);
    }
  }, [currentStep, isLastStep]);

  const closeReward = () => {
    setRewardViewState('none');
    clearResumeState();
    navigate('/portfolio');
  };

  const handleScopeClick = useCallback((event) => {
    const termEl = event.target?.closest?.('[data-term-highlight="true"]');
    if (!termEl || !selectionScopeRef.current?.contains(termEl)) return;

    const selectedText = window.getSelection?.()?.toString()?.trim();
    if (selectedText) return;

    event.preventDefault();
    openTermSheet(termEl.textContent || '');
  }, [openTermSheet]);

  // ──────────────────────────────────────────────
  // 텍스트 선택 → AI 튜터 CTA (최소 경로)
  //
  // 1) pointerup: 선택 확정 후 CTA 동기화
  // 2) outside pointerdown: 선택/CTA 1회 해제
  // ──────────────────────────────────────────────
  const clearNarrativeSelection = useCallback(() => {
    clearSelectionCtaState();
    setSelectionPopupPos({ x: 0, y: 0, placement: 'above' });
    try {
      window.getSelection()?.removeAllRanges();
    } catch {
      // ignore
    }
  }, [clearSelectionCtaState]);

  const syncSelectionCta = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      clearSelectionCtaState();
      return;
    }

    const text = sel.toString().trim();
    if (!text) {
      clearSelectionCtaState();
      return;
    }

    const range = sel.getRangeAt(0);
    const scope = selectionScopeRef.current;
    if (!scope || !scope.contains(range.startContainer) || !scope.contains(range.endContainer)) {
      clearSelectionCtaState();
      return;
    }

    // 전체 선택이 무시 대상(버튼 등) 내부인 경우 스킵
    const anchorEl = sel.anchorNode?.nodeType === Node.ELEMENT_NODE ? sel.anchorNode : sel.anchorNode?.parentElement;
    const focusEl = sel.focusNode?.nodeType === Node.ELEMENT_NODE ? sel.focusNode : sel.focusNode?.parentElement;
    if (anchorEl?.closest(SELECTION_IGNORE_SELECTOR) && focusEl?.closest(SELECTION_IGNORE_SELECTOR)) {
      clearSelectionCtaState();
      return;
    }

    const normalizedCaseId = Number(caseId);
    const safeCaseId = Number.isFinite(normalizedCaseId) ? normalizedCaseId : null;
    const selectionKey = `${safeCaseId ?? 'na'}:${stepConfig.key}:${text}`;
    const now = Date.now();
    if (lastSelectionTrackRef.current.key !== selectionKey || now - lastSelectionTrackRef.current.ts > 1500) {
      trackEvent('narrative_selection_cta_exposed', {
        case_id: safeCaseId,
        step_key: stepConfig.key,
        step_index: currentStep,
        selected_text_len: text.length,
      });
      lastSelectionTrackRef.current = { key: selectionKey, ts: now };
    }

    const rect = range.getBoundingClientRect();
    if (rect && (rect.width > 0 || rect.height > 0)) {
      const centerX = rect.left + (rect.width || 0) / 2;
      const popupHalfWidth = 130;
      const clampedX = Math.max(16 + popupHalfWidth, Math.min(window.innerWidth - 16 - popupHalfWidth, centerX));
      const aboveY = rect.top - 10;
      const belowY = rect.bottom + 10;
      const placement = aboveY >= 84 ? 'above' : 'below';
      setSelectionPopupPos({
        x: clampedX,
        y: placement === 'above' ? aboveY : belowY,
        placement,
      });
    }

    updateSelectionCtaState({
      active: true,
      text,
      prompt: `"${text}" 문구에 대해 설명해줘.`,
      context: {
        type: 'case',
        id: Number(caseId),
        stepKey: stepConfig.key,
        stepTitle: stepData?.title || stepConfig.title,
        stepContent: `[${stepData?.title || stepConfig.title} 단계 중 발췌]\n"${text}"`,
        sourcePage: 'narrative',
      },
    });
  }, [caseId, currentStep, stepConfig.key, stepConfig.title, stepData?.title, updateSelectionCtaState, clearSelectionCtaState]);

  const handleAskTutorFromSelection = useCallback(() => {
    const difficulty = settings?.difficulty || 'beginner';
    const normalizedCaseId = Number(caseId);
    const safeCaseId = Number.isFinite(normalizedCaseId) ? normalizedCaseId : null;
    trackEvent('narrative_selection_ask_click', {
      case_id: safeCaseId,
      step_key: stepConfig.key,
      step_index: currentStep,
      selected_text_len: selectionCtaState.text?.trim()?.length || 0,
      difficulty,
    });
    askTutorFromSelection(difficulty);
  }, [askTutorFromSelection, caseId, currentStep, selectionCtaState.text, settings?.difficulty, stepConfig.key]);

  // 단계 변경 시 선택 초기화
  useEffect(() => {
    clearNarrativeSelection();
  }, [currentStep, clearNarrativeSelection]);

  // narrative-selection-clear 이벤트 (튜터가 질문 제출 후 발생)
  useEffect(() => {
    const handler = () => {
      clearNarrativeSelection();
    };
    window.addEventListener('narrative-selection-clear', handler);
    return () => window.removeEventListener('narrative-selection-clear', handler);
  }, [clearNarrativeSelection]);

  // 언마운트 시 정리
  useEffect(() => () => clearSelectionCtaState(), [clearSelectionCtaState]);

  // 메인 선택 이벤트 리스너
  useEffect(() => {
    const onPointerDown = (e) => {
      if (e.target?.closest?.(CTA_GUARD_SELECTOR)) return;

      // scope 밖 클릭 → 네이티브 선택도 해제
      if (!selectionScopeRef.current?.contains(e.target)) {
        clearNarrativeSelection();
      }
    };

    const onPointerUp = (e) => {
      if (e.target?.closest?.(CTA_GUARD_SELECTOR)) return;
      requestAnimationFrame(syncSelectionCta);
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('pointerup', onPointerUp);

    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('pointerup', onPointerUp);
    };
  }, [syncSelectionCta, clearNarrativeSelection]);

  // ──────────────────────────────────────────────
  // 렌더링
  // ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse text-sm text-text-secondary">내러티브 로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-mobile rounded-2xl bg-surface-elevated p-6 text-center">
          <p className="text-sm text-error">{error}</p>
          <button
            type="button"
            onClick={() => navigate('/search')}
            className="mt-4 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white"
          >
            검색으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-background pb-28">
      <header className="sticky top-0 z-30 border-b border-white/60 bg-white/80 backdrop-blur-md">
        <div className="mx-auto w-full max-w-mobile px-4 pb-3 pt-4">
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex items-center gap-1 text-sm font-medium text-text-secondary transition hover:text-text-primary"
            >
              <span className="text-lg">‹</span>
              돌아가기
            </button>
            <span className="text-xs font-semibold text-text-muted">{currentStep + 1}/{totalSteps}</span>
          </div>

          <div className="flex items-center justify-center gap-2">
            {STEP_CONFIGS.map((config, idx) => (
              <button
                key={config.key}
                type="button"
                onClick={() => goToStep(idx)}
                className={`h-2.5 rounded-full transition-all ${
                  idx === currentStep ? 'w-8 bg-primary' : 'w-2.5 bg-[#d3d8df]'
                }`}
                aria-label={`${idx + 1}번째 내러티브 단계로 이동`}
              />
            ))}
          </div>
        </div>
      </header>

      <main
        ref={selectionScopeRef}
        data-selection-scope="narrative"
        onClick={handleScopeClick}
        className="mx-auto w-full max-w-mobile px-4 pt-4"
      >
        <AnimatePresence mode="wait" custom={direction}>
          <motion.section
            key={stepConfig.key}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.24, ease: 'easeInOut' }}
            onTouchStart={handleSwipeTouchStart}
            onTouchEnd={handleSwipeTouchEnd}
          >
            {stepData ? (
              <ContentTemplate
                stepConfig={stepConfig}
                stepData={stepData}
                stepTitle={stepTitle}
                oneLiner={data.one_liner}
                data={data}
              />
            ) : (
              <section className="px-3 py-5 text-center">
                <p className="text-sm text-text-secondary">이 단계의 콘텐츠를 준비 중입니다.</p>
              </section>
            )}

            <div className="mt-4 space-y-3">
              <NarrativeSources sources={stepData?.sources} />
              {isLastStep ? <NarrativeSources sources={data.sources} /> : null}
            </div>

            <div className="mt-6">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={goPrev}
                  disabled={currentStep === 0}
                  className="h-12 min-w-[96px] rounded-xl border border-border bg-white px-4 text-sm font-semibold text-text-secondary transition disabled:cursor-not-allowed disabled:opacity-40"
                >
                  이전
                </button>
                <button
                  type="button"
                  onClick={goNext}
                  className="h-12 flex-1 rounded-xl bg-primary px-4 text-sm font-semibold text-white transition hover:bg-primary-hover"
                >
                  {isLastStep ? '보상 받기' : '다음'}
                </button>
              </div>
            </div>
          </motion.section>
        </AnimatePresence>
      </main>

      {selectionCtaState.active && selectionPopupPos.x > 0 ? (
        <div
          id="narrative-selection-cta"
          className="fixed z-50"
          style={{
            left: `${selectionPopupPos.x}px`,
            top: `${selectionPopupPos.y}px`,
            transform: selectionPopupPos.placement === 'above' ? 'translate(-50%, -100%)' : 'translate(-50%, 0%)',
          }}
        >
          <div className="flex items-center gap-2 rounded-full border border-primary/20 bg-white/95 px-2 py-1 shadow-lg backdrop-blur-sm">
            <button
              type="button"
              onClick={clearNarrativeSelection}
              className="h-8 rounded-full border border-border bg-white px-3 text-xs font-semibold text-text-secondary transition hover:bg-surface"
            >
              해제
            </button>
            <button
              type="button"
              onClick={handleAskTutorFromSelection}
              disabled={isTutorLoading}
              className="h-8 rounded-full bg-primary px-3 text-xs font-semibold text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-70"
            >
              AI 튜터에게 질문
            </button>
          </div>
        </div>
      ) : null}

      {rewardError && rewardViewState === 'none' ? (
        <div className="fixed bottom-20 left-0 right-0 z-40 px-4">
          <div className="mx-auto w-full max-w-mobile rounded-xl bg-error px-4 py-3 text-center text-sm font-medium text-white">
            {rewardError}
          </div>
        </div>
      ) : null}

      <AnimatePresence>
        {isResumeDialogOpen ? (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/45"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.div
              className="fixed inset-0 z-50 flex items-center justify-center px-4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
            >
              <div className="w-full max-w-mobile rounded-2xl bg-surface-elevated p-6 shadow-xl">
                <h3 className="text-base font-bold text-text-primary">중간 지점부터 보시겠습니까?</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  이전에 보던 내러티브 진행 지점이 있습니다.
                </p>
                <div className="mt-5 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleResumeFromBeginning}
                    className="h-11 flex-1 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-text-secondary"
                  >
                    처음부터 보기
                  </button>
                  <button
                    type="button"
                    onClick={handleResumeFromSavedPoint}
                    className="h-11 flex-1 rounded-xl bg-primary px-4 text-sm font-semibold text-white"
                  >
                    이어보기
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      {rewardViewState !== 'none' ? (
        <RewardResultScreen
          mode={rewardViewState}
          rewardAmount={rewardData?.base_reward}
          onBack={() => setRewardViewState('none')}
          onPrimaryAction={closeReward}
        />
      ) : null}
    </div>
  );
}
