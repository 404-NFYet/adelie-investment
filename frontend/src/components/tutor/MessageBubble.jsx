/**
 * MessageBubble - 채팅 메시지 렌더링 컴포넌트
 * Message, SourceBadge, VisualizationMessage, TypingIndicator 포함
 */
import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';
import PenguinLoading from '../common/PenguinLoading';
import ResponsivePlotly from '../charts/ResponsivePlotly';
import { normalizeLayout } from '../../utils/plotly/normalizeLayout';
import { normalizeTraces } from '../../utils/plotly/normalizeTraces';

// 출처 분류 체계
const SOURCE_LABELS = {
  glossary:    { icon: '\uD83D\uDCD6', label: '자체 용어집',    desc: '투자 용어 사전 (DB)' },
  case:        { icon: '\uD83D\uDCCB', label: '역사적 사례',    desc: 'DB 저장 과거 사례 분석' },
  report:      { icon: '\uD83D\uDCC4', label: '증권사 리포트',  desc: '네이버 금융 크롤링' },
  dart:        { icon: '\uD83C\uDFDB\uFE0F', label: 'DART 공시', desc: '금융감독원 전자공시' },
  news:        { icon: '\uD83D\uDCF0', label: '뉴스 기사',      desc: '언론 보도 링크' },
  stock_price: { icon: '\uD83D\uDCC8', label: '실시간 시세',    desc: 'pykrx 주가 조회' },
  financial:   { icon: '\uD83D\uDCB9', label: '재무제표',       desc: 'FinanceDataReader' },
  web:         { icon: '\uD83C\uDF10', label: '웹 검색',        desc: 'Perplexity 검색' },
};

function normalizeMathDelimiters(content) {
  if (!content) return '';

  let normalized = String(content).replace(/\r\n/g, '\n');

  // MathJax 스타일 블록 수식(\[...\])을 KaTeX 호환 블록($$...$$)으로 정규화
  normalized = normalized.replace(
    /(?:^|\n)\s*\\\[\s*([\s\S]*?)\s*\\?\]\s*(?=\n|$)/g,
    (_, expr) => `\n$$\n${expr.trim()}\n$$\n`,
  );

  // MathJax 스타일 인라인 수식(\(...\))을 KaTeX 호환 인라인($...$)으로 정규화
  normalized = normalized.replace(/\\\(\s*([\s\S]*?)\s*\\\)/g, (_, expr) => `$${expr.trim()}$`);

  return normalized;
}

function SourceBadge({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-primary transition-colors">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
        <span className="font-medium">{sources.length}개 출처</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div className="mt-2 space-y-2 pl-0.5">
          {sources.map((s, i) => {
            const meta = SOURCE_LABELS[s.type] || SOURCE_LABELS.web;
            const hasUrl = s.url && (s.url.startsWith('http') || s.url.startsWith('/'));
            const isExternal = s.url && s.url.startsWith('http');
            return (
              <div key={i} className="flex items-start gap-2 text-[11px] group">
                <span className="mt-0.5 text-sm flex-shrink-0" title={meta.desc}>{meta.icon}</span>
                <div className="min-w-0 flex-1">
                  <span className="text-[10px] text-text-secondary">{meta.label}</span>
                  <div className="mt-0.5">
                    {hasUrl ? (
                      <a
                        href={s.url}
                        target={isExternal ? '_blank' : '_self'}
                        rel={isExternal ? 'noopener noreferrer' : undefined}
                        className="text-primary hover:underline font-medium"
                      >
                        {s.title}
                        {isExternal && <span className="ml-0.5 text-[9px] opacity-50">\u2197</span>}
                      </a>
                    ) : (
                      <span className="font-medium text-text-primary">{s.title}</span>
                    )}
                    {s.content && <span className="text-text-secondary ml-1">— {s.content.slice(0, 60)}</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * 레거시 HTML에서 Plotly data/layout 추출 (하위 호환용)
 * Plotly.newPlot('id', data, layout) 또는 var data/layout 패턴 매칭
 */
function extractPlotlyDataFromHtml(html) {
  try {
    // 패턴 1: Plotly.newPlot('id', [...], {...})
    const plotCallMatch = html.match(
      /Plotly\.(?:newPlot|react)\s*\(\s*['"][^'"]*['"]\s*,\s*([\s\S]+?)\s*,\s*(\{[\s\S]+?\})\s*[,)]/
    );
    if (plotCallMatch) {
      // eslint-disable-next-line no-new-func
      const data = new Function(`return ${plotCallMatch[1]}`)();
      // eslint-disable-next-line no-new-func
      const layout = new Function(`return ${plotCallMatch[2]}`)();
      if (Array.isArray(data)) return { data, layout: layout || {} };
    }
    // 패턴 2: var data = [...]; var layout = {...};
    const dataMatch = html.match(/(?:var|let|const)\s+data\s*=\s*([\s\S]+?);\s*(?:var|let|const)\s+layout/);
    const layoutMatch = html.match(/(?:var|let|const)\s+layout\s*=\s*([\s\S]+?);\s*(?:Plotly|<\/script)/);
    if (dataMatch && layoutMatch) {
      // eslint-disable-next-line no-new-func
      const data = new Function(`return ${dataMatch[1].trim()}`)();
      // eslint-disable-next-line no-new-func
      const layout = new Function(`return ${layoutMatch[1].trim()}`)();
      if (Array.isArray(data)) return { data, layout: layout || {} };
    }
  } catch (e) {
    console.warn('Plotly HTML 파싱 실패:', e);
  }
  return null;
}

function VisualizationMessage({ message }) {
  const [expanded, setExpanded] = useState(false);

  // 차트 데이터 결정: JSON(chartData) 우선 → 레거시 HTML 폴백
  let chartData = null;
  if (message.chartData && message.chartData.data) {
    chartData = message.chartData;
  } else if (message.format === 'html' && message.content) {
    chartData = extractPlotlyDataFromHtml(message.content);
  }

  const normalizedData = normalizeTraces(chartData?.data);
  const hasChart = normalizedData.length > 0;
  const hasPie = normalizedData.some((trace) => trace.type === 'pie');
  const normalizedLayout = normalizeLayout(chartData?.layout || {}, { hasPie, clearTitle: false });
  const fixedHeight = expanded ? 440 : 280;

  return (
    <motion.div className="mb-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <img src="/images/penguin-3d.png" alt="" className="w-5 h-5 rounded-full object-cover" />
        <span className="text-xs text-text-secondary">차트</span>
        {message.executionTime && <span className="text-[10px] text-text-secondary ml-auto">{message.executionTime}ms</span>}
      </div>
      <div className="max-w-[480px] overflow-hidden rounded-2xl border border-border bg-white p-2 transition-all">
        {hasChart ? (
          <ResponsivePlotly
            data={normalizedData}
            layout={normalizedLayout}
            mode="fixed"
            fixedHeight={fixedHeight}
            minHeight={fixedHeight}
            maxHeight={fixedHeight}
            loadingText="차트 로딩 중..."
            emptyText="차트를 생성할 수 없습니다"
          />
        ) : (
          <div className="flex items-center justify-center text-sm text-text-secondary" style={{ height: fixedHeight }}>
            차트를 생성할 수 없습니다
          </div>
        )}
      </div>
      {hasChart && (
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-text-secondary hover:text-primary transition-colors mt-1">
          {expanded ? '축소' : '확대'}
        </button>
      )}
    </motion.div>
  );
}

export function TypingIndicator() {
  return (
    <motion.div className="flex justify-start mb-3" initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}>
      <div className="bg-surface px-3 py-2 rounded-2xl rounded-bl-md">
        <PenguinLoading message="분석 중이에요..." />
      </div>
    </motion.div>
  );
}

export default React.memo(function Message({ message }) {
  const markdownContent = useMemo(
    () => normalizeMathDelimiters(message.content),
    [message.content],
  );
  if (message.role === 'visualization') return <VisualizationMessage message={message} />;

  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <motion.div className="flex justify-end mb-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="max-w-[85%] px-4 py-2.5 rounded-2xl bg-primary text-white rounded-br-md">
          <p className="text-sm">{message.content}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className="flex justify-start mb-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="max-w-[90%]">
        <div className="flex items-center gap-1.5 mb-1.5">
          <img src="/images/penguin-3d.png" alt="" className="w-5 h-5 rounded-full object-cover" />
          <span className="text-xs text-text-secondary font-medium">AI 튜터</span>
        </div>
        <div className={`px-4 py-3 rounded-2xl rounded-tl-md ${message.isError ? 'bg-error-light text-error border border-error/20' : 'bg-surface border border-border'}`}>
          {message.isError ? <p className="text-sm">{message.content}</p> : (
            <div className="text-sm leading-relaxed text-text-primary prose prose-sm prose-headings:text-text-primary prose-strong:text-text-primary prose-code:text-primary prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeRaw, rehypeKatex]}>
                {markdownContent}
              </ReactMarkdown>
            </div>
          )}
          {message.isStreaming && <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 rounded-sm" />}
        </div>
        {message.sources && message.sources.length > 0 && <SourceBadge sources={message.sources} />}
      </div>
    </motion.div>
  );
})
