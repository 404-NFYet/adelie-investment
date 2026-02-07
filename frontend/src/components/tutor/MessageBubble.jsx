/**
 * MessageBubble - 채팅 메시지 렌더링 컴포넌트
 * Message, SourceBadge, VisualizationMessage, TypingIndicator 포함
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { renderMarkdown } from '../../utils/markdown';
import PenguinLoading from '../common/PenguinLoading';

// 출처 분류 체계 (온톨로지 기반)
const SOURCE_LABELS = {
  glossary:    { icon: '\uD83D\uDCD6', label: '자체 용어집',    desc: '투자 용어 사전 (DB)' },
  ontology:    { icon: '\uD83D\uDD17', label: '온톨로지',       desc: 'Neo4j 기업 관계 그래프' },
  case:        { icon: '\uD83D\uDCCB', label: '역사적 사례',    desc: 'DB 저장 과거 사례 분석' },
  report:      { icon: '\uD83D\uDCC4', label: '증권사 리포트',  desc: '네이버 금융 크롤링' },
  dart:        { icon: '\uD83C\uDFDB\uFE0F', label: 'DART 공시', desc: '금융감독원 전자공시' },
  news:        { icon: '\uD83D\uDCF0', label: '뉴스 기사',      desc: '언론 보도 링크' },
  stock_price: { icon: '\uD83D\uDCC8', label: '실시간 시세',    desc: 'pykrx 주가 조회' },
  financial:   { icon: '\uD83D\uDCB9', label: '재무제표',       desc: 'FinanceDataReader' },
  company:     { icon: '\uD83C\uDFE2', label: '기업 관계',      desc: 'Neo4j 공급망/경쟁사' },
  web:         { icon: '\uD83C\uDF10', label: '웹 검색',        desc: 'Perplexity 검색' },
};

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

function VisualizationMessage({ message }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <motion.div className="mb-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <img src="/images/penguin-3d.png" alt="" className="w-5 h-5 rounded-full object-cover" />
        <span className="text-xs text-text-secondary">차트</span>
        {message.executionTime && <span className="text-[10px] text-text-secondary ml-auto">{message.executionTime}ms</span>}
      </div>
      <div className={`rounded-2xl border border-border overflow-hidden bg-white transition-all ${expanded ? 'h-[400px]' : 'h-[280px]'}`}>
        {message.format === 'html' ? (
          <iframe srcDoc={message.content} className="w-full h-full border-0" sandbox="allow-scripts" title="차트" />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-text-secondary">차트를 불러올 수 없습니다</div>
        )}
      </div>
      <button onClick={() => setExpanded(!expanded)} className="text-xs text-text-secondary hover:text-primary transition-colors mt-1">{expanded ? '축소' : '확대'}</button>
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

export default function Message({ message }) {
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
            <div className="text-sm leading-relaxed text-text-primary prose-sm" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
          )}
          {message.isStreaming && <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 rounded-sm" />}
        </div>
        {message.sources && message.sources.length > 0 && <SourceBadge sources={message.sources} />}
      </div>
    </motion.div>
  );
}
