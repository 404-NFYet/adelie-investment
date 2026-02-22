import { lazy, Suspense, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';

const ResponsivePlotly = lazy(() => import('../charts/ResponsivePlotly'));

function tryParseChartJson(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed?.data)) return parsed;
  } catch {
    // not valid chart JSON
  }
  return null;
}

function ChartCodeBlock({ children }) {
  const chart = useMemo(() => tryParseChartJson(String(children || '')), [children]);
  if (!chart) return <pre><code>{children}</code></pre>;

  return (
    <Suspense fallback={<div className="flex h-[220px] items-center justify-center text-[13px] text-[#8B95A1]">차트 로딩 중...</div>}>
      <ResponsivePlotly
        data={chart.data}
        layout={chart.layout || {}}
        config={chart.config || {}}
        mode="ratio"
        className="my-3"
      />
    </Suspense>
  );
}

function CodeBlockRenderer({ className, children, ...rest }) {
  const lang = String(className || '').replace('language-', '');
  if (lang === 'chart' || lang === 'plotly') {
    return <ChartCodeBlock>{children}</ChartCodeBlock>;
  }
  return <code className={className} {...rest}>{children}</code>;
}

function ActionButtons({ actions, onActionClick }) {
  if (!Array.isArray(actions) || actions.length === 0) return null;

  return (
    <section className="grid grid-cols-2 gap-2">
      {actions.map((action) => {
        const isTool = action.type === 'tool';
        return (
          <button
            key={action.id || action.label}
            type="button"
            onClick={() => onActionClick(action)}
            className={
              isTool
                ? 'rounded-[12px] border border-[#FF6B00]/30 bg-[#FFF7F0] px-3 py-2.5 text-[12px] font-semibold text-[#FF6B00] break-keep active:bg-[#FFE5D3]'
                : 'rounded-[12px] border border-[var(--agent-border)] bg-white px-3 py-2.5 text-[12px] font-medium text-[#4E5968] break-keep active:bg-[#F2F4F6]'
            }
          >
            {isTool && (
              <svg className="mr-1 inline-block align-[-2px]" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m15 12-8.5 8.5c-.83.83-2.17.83-3 0s-.83-2.17 0-3L12 9" />
                <path d="M17.64 15 22 10.64" />
                <path d="m20.91 11.7-1.25-1.25c-.6-.6-.93-1.4-.93-2.25V6.5l-3-2.5H13l-2.5 3v1.75c0 .85-.33 1.65-.93 2.25L8.32 12.2" />
              </svg>
            )}
            {action.label || action}
          </button>
        );
      })}
    </section>
  );
}

const markdownComponents = {
  code: CodeBlockRenderer,
};

export default function AgentCanvasSections({
  canvasState,
  onActionClick,
  contentRef = null,
}) {
  const actions = Array.isArray(canvasState.actions) ? canvasState.actions : [];
  const markdownText = canvasState.rawAssistantText || '';

  if (canvasState.viewType === 'empty') {
    return (
      <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-4">
        <p className="text-[14px] leading-relaxed text-[#8B95A1]">
          질문을 입력하면 맥락에 맞는 요약을 정리해드려요.
        </p>
      </section>
    );
  }

  return (
    <>
      <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-4">
        <div className="max-w-full overflow-x-auto">
          <div
            ref={contentRef}
            className="prose prose-sm max-w-none touch-pan-y text-[14px] leading-[1.75] text-[#333D4B] prose-headings:text-[#191F28] prose-strong:text-[#191F28] prose-code:rounded prose-code:bg-[#F2F4F6] prose-code:px-1 prose-code:py-0.5 prose-code:text-[#374151]"
          >
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeRaw, rehypeKatex]}
              components={markdownComponents}
            >
              {markdownText}
            </ReactMarkdown>
          </div>
        </div>
      </section>

      <ActionButtons actions={actions} onActionClick={onActionClick} />
    </>
  );
}
