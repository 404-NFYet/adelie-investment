/**
 * ChatBubble - 채팅 메시지 컴포넌트
 * 
 * - 사용자: 주황색 말풍선 (우측)
 * - 에이전트: 말풍선 없이 흰 바탕에 마크다운 렌더링
 * - 시각화: Plotly/HTML 인라인 렌더링
 */
import React, { useMemo, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';

function normalizeMathDelimiters(content) {
  if (!content) return '';
  let normalized = String(content).replace(/\r\n/g, '\n');
  normalized = normalized.replace(
    /(?:^|\n)\s*\\\[\s*([\s\S]*?)\s*\\?\]\s*(?=\n|$)/g,
    (_, expr) => `\n$$\n${expr.trim()}\n$$\n`,
  );
  normalized = normalized.replace(/\\\(\s*([\s\S]*?)\s*\\\)/g, (_, expr) => `$${expr.trim()}$`);
  return normalized;
}

const markdownComponents = {
  h1: ({ children }) => (
    <h1 className="text-xl font-bold text-[#191F28] mt-6 mb-3 first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-bold text-[#191F28] mt-5 mb-2.5 first:mt-0 pb-2 border-b border-[#F2F4F6]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold text-[#191F28] mt-4 mb-2 first:mt-0">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-[15px] leading-[1.8] text-[#333D4B] mb-4 last:mb-0">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-5 space-y-2 mb-4 last:mb-0 text-[15px] text-[#333D4B]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-5 space-y-2 mb-4 last:mb-0 text-[15px] text-[#333D4B]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="leading-[1.7]">{children}</li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-[#FF6B00] bg-[#FFF8F3] pl-4 pr-4 py-3 my-4 rounded-r-lg text-[#6B7684]">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-4 rounded-xl border border-[#E5E8EB] shadow-sm">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-[#F7F8FA]">{children}</thead>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-[#F2F4F6]">{children}</tbody>
  ),
  tr: ({ children }) => (
    <tr className="hover:bg-[#FAFBFC] transition-colors">{children}</tr>
  ),
  th: ({ children }) => (
    <th className="px-4 py-3 text-left font-semibold text-[#191F28] text-sm whitespace-nowrap border-b-2 border-[#E5E8EB]">{children}</th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-[#4E5968] text-sm">{children}</td>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-[#191F28]">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-[#6B7684]">{children}</em>
  ),
  code: ({ inline, children, className }) => {
    if (inline) {
      return (
        <code className="bg-[#F2F4F6] text-[#D63384] px-1.5 py-0.5 rounded text-[13px] font-mono">
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-[#1E293B] text-[#E2E8F0] p-4 rounded-xl overflow-x-auto my-4 text-[13px] font-mono">
        <code className={className}>{children}</code>
      </pre>
    );
  },
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[#FF6B00] hover:underline font-medium"
    >
      {children}
    </a>
  ),
  hr: () => <div className="my-4" />,
  img: ({ alt }) => (
    <span className="inline-flex items-center gap-1 px-2 py-1 bg-[#F7F8FA] rounded text-xs text-[#8B95A1]">
      <span>📊</span>
      <span>{alt || '차트 데이터'}</span>
    </span>
  ),
};

function UserBubble({ content }) {
  return (
    <motion.div
      className="flex justify-end mb-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="max-w-[80%] px-4 py-3 bg-[#FF6B00] text-white rounded-2xl rounded-br-md shadow-sm">
        <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </motion.div>
  );
}

function AssistantContent({ content, isStreaming, sources }) {
  const markdownContent = useMemo(
    () => normalizeMathDelimiters(content),
    [content],
  );

  return (
    <motion.div
      className="mb-6"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="prose-agent">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeRaw, rehypeKatex]}
          components={markdownComponents}
        >
          {markdownContent}
        </ReactMarkdown>
      </div>
      {isStreaming && (
        <span className="inline-block w-1.5 h-5 bg-[#FF6B00] animate-pulse ml-0.5 rounded-sm" />
      )}

      {sources && sources.length > 0 && (
        <SourceBadge sources={sources} />
      )}
    </motion.div>
  );
}

function SourceBadge({ sources }) {
  const [open, setOpen] = React.useState(false);

  const SOURCE_LABELS = {
    glossary: { icon: '📖', label: '용어집' },
    case: { icon: '📋', label: '사례' },
    report: { icon: '📄', label: '리포트' },
    dart: { icon: '🏛️', label: 'DART' },
    news: { icon: '📰', label: '뉴스' },
    stock_price: { icon: '📈', label: '시세' },
    financial: { icon: '💹', label: '재무' },
    web: { icon: '🌐', label: '웹' },
  };

  return (
    <div className="mt-4 pt-3 border-t border-[#F2F4F6]">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-[#8B95A1] hover:text-[#FF6B00] transition-colors"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>{sources.length}개 출처 참고</span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="mt-3 space-y-2">
          {sources.map((s, i) => {
            const meta = SOURCE_LABELS[s.type] || SOURCE_LABELS.web;
            const hasUrl = s.url && (s.url.startsWith('http') || s.url.startsWith('/'));
            return (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span>{meta.icon}</span>
                {hasUrl ? (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#FF6B00] hover:underline"
                  >
                    {s.title}
                  </a>
                ) : (
                  <span className="text-[#4E5968]">{s.title}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ErrorContent({ content }) {
  return (
    <motion.div
      className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center gap-2 text-red-600">
        <span className="text-base">⚠️</span>
        <p className="text-sm">{content}</p>
      </div>
    </motion.div>
  );
}

function VisualizationContent({ message }) {
  const { chartData, content, format } = message;
  const containerRef = useRef(null);

  useEffect(() => {
    if (chartData && chartData.data && containerRef.current && window.Plotly) {
      window.Plotly.newPlot(containerRef.current, chartData.data, {
        ...chartData.layout,
        margin: { t: 40, r: 20, b: 40, l: 50 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Pretendard, sans-serif', size: 12 },
      }, { responsive: true, displayModeBar: false });
    }
  }, [chartData]);

  if (chartData && chartData.data) {
    return (
      <motion.div
        className="mb-6"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="rounded-xl border border-[#E5E8EB] bg-white p-4 shadow-sm">
          {chartData.layout?.title && (
            <h3 className="text-base font-semibold text-[#191F28] mb-3">
              {chartData.layout.title}
            </h3>
          )}
          <div ref={containerRef} className="w-full h-64" />
        </div>
      </motion.div>
    );
  }

  if (content && format === 'html') {
    return (
      <motion.div
        className="mb-6"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div
          className="rounded-xl border border-[#E5E8EB] bg-white p-4 shadow-sm overflow-x-auto visualization-html"
          dangerouslySetInnerHTML={{ __html: content }}
        />
      </motion.div>
    );
  }

  return null;
}

export default React.memo(function ChatBubble({ message }) {
  if (message.role === 'user') {
    return <UserBubble content={message.content} />;
  }

  if (message.role === 'assistant') {
    return (
      <AssistantContent
        content={message.content}
        isStreaming={message.isStreaming}
        sources={message.sources}
      />
    );
  }

  if (message.role === 'visualization') {
    return <VisualizationContent message={message} />;
  }

  if (message.isError) {
    return <ErrorContent content={message.content} />;
  }

  return null;
});
