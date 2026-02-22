import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';

function formatMetricValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value || '-');
  return `${numeric.toLocaleString('ko-KR')}원`;
}

function ActionButtons({ actions, onActionClick }) {
  if (!Array.isArray(actions) || actions.length === 0) return null;

  return (
    <section className="grid grid-cols-2 gap-2">
      {actions.map((action) => (
        <button
          key={action.id || action.label}
          type="button"
          onClick={() => onActionClick(action)}
          className="rounded-[12px] border border-[var(--agent-border)] bg-white px-3 py-2.5 text-[12px] font-medium text-[#4E5968] break-keep active:bg-[#F2F4F6]"
        >
          {action.label || action}
        </button>
      ))}
    </section>
  );
}

function SourceKindBadge({ kind }) {
  const normalized = String(kind || 'internal').toLowerCase();
  const labelByKind = {
    internal: '내부',
    dart: '공시',
    news: '뉴스',
    web: '웹',
  };
  return (
    <span className="rounded-full bg-[#F2F4F6] px-2 py-0.5 text-[10px] font-semibold text-[#6B7684]">
      {labelByKind[normalized] || normalized}
    </span>
  );
}

export default function AgentCanvasSections({
  canvasState,
  onActionClick,
  contentRef = null,
}) {
  const actions = Array.isArray(canvasState.actions) ? canvasState.actions : [];
  const markdownText = canvasState.rawAssistantText || '';
  const structured = canvasState.structured || null;
  const sources = Array.isArray(canvasState.sources) ? canvasState.sources : [];
  const metricRows = Array.isArray(canvasState.metricRows) ? canvasState.metricRows : [];

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
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeRaw, rehypeKatex]}>
              {markdownText}
            </ReactMarkdown>
          </div>
        </div>
      </section>

      {structured && (
        <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-3">
          <p className="text-[11px] font-bold uppercase tracking-wider text-[#8B95A1]">요약</p>
          <p className="mt-1 text-[14px] font-semibold text-[#191F28]">{structured.summary || canvasState.keyPoint}</p>

          {Array.isArray(structured.key_points) && structured.key_points.length > 0 && (
            <ul className="mt-2 space-y-1.5 text-[13px] text-[#4E5968]">
              {structured.key_points.map((point, index) => (
                <li key={`${point}-${index}`} className="flex gap-2">
                  <span className="mt-[9px] h-1 w-1 rounded-full bg-[#D1D6DB]" />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {metricRows.length > 0 && (
        <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-3">
          <p className="text-[11px] font-bold uppercase tracking-wider text-[#8B95A1]">핵심 수치</p>
          <div className="mt-2 grid grid-cols-1 gap-1.5">
            {metricRows.map((row) => (
              <div key={row.key} className="flex items-center justify-between rounded-[10px] bg-[#F8FAFC] px-3 py-2">
                <span className="text-[12px] font-medium text-[#6B7684]">{row.label}</span>
                <span className="text-[13px] font-semibold text-[#191F28]">{formatMetricValue(row.value)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {sources.length > 0 && (
        <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-3">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#8B95A1]">근거 출처</p>
            <span className="text-[11px] text-[#B0B8C1]">{sources.length}건</span>
          </div>
          <ul className="mt-2 space-y-2">
            {sources.slice(0, 6).map((source, index) => (
              <li key={`${source.title}-${index}`} className="rounded-[10px] border border-[#EEF1F4] px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <SourceKindBadge kind={source.source_kind} />
                  {source.is_reachable === true && (
                    <span className="text-[10px] font-semibold text-[#16A34A]">링크 확인됨</span>
                  )}
                  {source.is_reachable === false && (
                    <span className="text-[10px] font-semibold text-[#DC2626]">링크 확인 실패</span>
                  )}
                </div>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block text-[12px] font-medium text-[#2563EB] underline-offset-2 hover:underline"
                  >
                    {source.title}
                  </a>
                ) : (
                  <p className="mt-1 text-[12px] font-medium text-[#4E5968]">{source.title}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <ActionButtons actions={actions} onActionClick={onActionClick} />
    </>
  );
}
