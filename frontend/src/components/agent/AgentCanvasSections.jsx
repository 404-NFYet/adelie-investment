import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';

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

export default function AgentCanvasSections({
  canvasState,
  onActionClick,
}) {
  const actions = Array.isArray(canvasState.actions) ? canvasState.actions : [];
  const markdownText = canvasState.rawAssistantText || '';
  const structured = canvasState.structured || null;

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
        <div className="overflow-x-auto max-w-full">
          <div className="prose prose-sm max-w-none text-[14px] leading-[1.75] text-[#333D4B] prose-headings:text-[#191F28] prose-strong:text-[#191F28] prose-code:rounded prose-code:bg-[#F2F4F6] prose-code:px-1 prose-code:py-0.5 prose-code:text-[#374151]">
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

      <ActionButtons actions={actions} onActionClick={onActionClick} />
    </>
  );
}
