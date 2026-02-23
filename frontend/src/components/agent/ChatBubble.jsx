/**
 * ChatBubble - 말풍선 컴포넌트
 * 
 * - 사용자: 주황색 배경(#FF6B00) + 흰색 텍스트, 우측 정렬
 * - 에이전트: 흰색 배경 + 검은색 텍스트, 좌측 정렬
 * - 마크다운 렌더링 개선 (줄 간격, 제목, 불렛, 표, 인용구)
 */
import React, { useMemo } from 'react';
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
    <h1 className="text-lg font-bold text-[#191F28] mt-4 mb-2 first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-bold text-[#191F28] mt-3 mb-2 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-bold text-[#191F28] mt-3 mb-1.5 first:mt-0">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-sm leading-[1.7] text-[#333D4B] mb-2.5 last:mb-0">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-4 space-y-1 mb-3 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-4 space-y-1 mb-3 last:mb-0">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-sm leading-[1.6] text-[#333D4B]">{children}</li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-[#FFB380] bg-[#FFF8F3] pl-4 pr-3 py-2 my-3 rounded-r-lg italic text-[#6B7684]">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-[#F7F8FA]">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="border border-[#E5E8EB] px-3 py-2 text-left font-semibold text-[#333D4B]">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-[#E5E8EB] px-3 py-2 text-[#4E5968]">{children}</td>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-[#191F28]">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-[#6B7684]">{children}</em>
  ),
  code: ({ inline, children }) => {
    if (inline) {
      return (
        <code className="bg-[#F2F4F6] text-[#D63384] px-1.5 py-0.5 rounded text-[13px] font-mono">
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-[#1E293B] text-[#E2E8F0] p-3 rounded-lg overflow-x-auto my-3 text-[13px] font-mono">
        <code>{children}</code>
      </pre>
    );
  },
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[#FF6B00] hover:underline"
    >
      {children}
    </a>
  ),
};

function UserBubble({ content }) {
  return (
    <motion.div
      className="flex justify-end mb-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="max-w-[85%] px-4 py-2.5 bg-[#FF6B00] text-white rounded-2xl rounded-br-md shadow-sm">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </motion.div>
  );
}

function AssistantBubble({ content, isStreaming, sources }) {
  const markdownContent = useMemo(
    () => normalizeMathDelimiters(content),
    [content],
  );

  return (
    <motion.div
      className="flex items-start gap-2 mb-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="w-7 h-7 rounded-full bg-[#F2F4F6] flex items-center justify-center flex-shrink-0 mt-0.5">
        <img src="/images/penguin-3d.png" alt="" className="w-5 h-5" />
      </div>
      <div className="max-w-[88%] min-w-0">
        <div className="bg-white border border-[#E5E8EB] rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
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
            <span className="inline-block w-1.5 h-4 bg-[#FF6B00] animate-pulse ml-0.5 rounded-sm" />
          )}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <SourceBadge sources={sources} />
        )}
      </div>
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
    <div className="mt-2 pl-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-[#8B95A1] hover:text-[#FF6B00] transition-colors"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>{sources.length}개 출처</span>
        <svg
          width="10"
          height="10"
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
        <div className="mt-2 space-y-1.5">
          {sources.map((s, i) => {
            const meta = SOURCE_LABELS[s.type] || SOURCE_LABELS.web;
            const hasUrl = s.url && (s.url.startsWith('http') || s.url.startsWith('/'));
            return (
              <div key={i} className="flex items-center gap-2 text-[11px]">
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

function ErrorBubble({ content }) {
  return (
    <motion.div
      className="flex items-start gap-2 mb-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-red-500 text-sm">!</span>
      </div>
      <div className="max-w-[88%]">
        <div className="bg-red-50 border border-red-200 rounded-2xl rounded-tl-md px-4 py-3">
          <p className="text-sm text-red-600">{content}</p>
        </div>
      </div>
    </motion.div>
  );
}

export default React.memo(function ChatBubble({ message }) {
  if (message.role === 'user') {
    return <UserBubble content={message.content} />;
  }

  if (message.role === 'assistant') {
    return (
      <AssistantBubble
        content={message.content}
        isStreaming={message.isStreaming}
        sources={message.sources}
      />
    );
  }

  if (message.isError) {
    return <ErrorBubble content={message.content} />;
  }

  return null;
});
