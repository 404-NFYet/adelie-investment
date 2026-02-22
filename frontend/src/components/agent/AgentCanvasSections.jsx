export default function AgentCanvasSections({
  canvasState,
  onActionClick,
}) {
  const actions = Array.isArray(canvasState.actions) ? canvasState.actions : [];
  const showActions = actions.length > 0;

  if (canvasState.viewType === 'empty') {
    return (
      <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-4">
        <p className="text-[14px] leading-relaxed text-[#8B95A1]">
          질문을 입력하면 맥락에 맞는 요약을 정리해드려요.
        </p>
      </section>
    );
  }

  if (canvasState.viewType === 'plain') {
    return (
      <>
        <section className="rounded-[var(--agent-radius-sm)] border border-[var(--agent-border)] bg-white px-4 py-4">
          <div className="space-y-2.5">
            {canvasState.textBlocks.map((item, index) => (
              <p key={`${item.slice(0, 24)}-${index}`} className="text-[14px] leading-[1.7] text-[#333D4B]">
                {item}
              </p>
            ))}
          </div>
        </section>

        {showActions && (
          <section className="grid grid-cols-2 gap-2">
            {actions.map((action) => (
              <button
                key={action.id || action.label}
                type="button"
                onClick={() => onActionClick(action)}
                className="rounded-[12px] border border-[var(--agent-border)] bg-white px-3 py-2.5 text-[13px] font-medium text-[#4E5968] active:bg-[#F2F4F6]"
              >
                {action.label || action}
              </button>
            ))}
          </section>
        )}
      </>
    );
  }

  return (
    <>
      {/* KEY POINT 카드 */}
      <section className="rounded-[var(--agent-radius-sm)] bg-[#F2F4F6] px-4 py-3.5">
        <p className="mb-1.5 text-[11px] font-bold uppercase tracking-widest text-[#8B95A1]">KEY POINT</p>
        <p className="text-[15px] font-bold leading-[1.5] text-[#191F28]">{canvasState.keyPoint}</p>
      </section>

      {/* 핵심 해석 */}
      <section className="space-y-3 px-1">
        <div className="flex items-center gap-2">
          <span className="inline-block h-4 w-1 rounded-full bg-[#FF6B00]" />
          <h2 className="text-[16px] font-bold text-[#191F28]">핵심 해석</h2>
        </div>

        <p className="text-[14px] leading-[1.7] text-[#4E5968]">
          {canvasState.explanation}
        </p>

        {canvasState.bullets.length > 0 && (
          <ul className="space-y-1.5 text-[13px] leading-[1.6] text-[#333D4B]">
            {canvasState.bullets.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-2">
                <span className="mt-[9px] h-1 w-1 flex-shrink-0 rounded-full bg-[#D1D6DB]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}

        {canvasState.quote && (
          <blockquote className="border-l-2 border-[#E8EBED] pl-3 text-[13px] italic leading-[1.6] text-[#8B95A1]">
            {canvasState.quote}
          </blockquote>
        )}
      </section>

      {showActions && (
        <section className="grid grid-cols-2 gap-2">
          {actions.map((action) => (
            <button
              key={action.id || action.label}
              type="button"
              onClick={() => onActionClick(action)}
              className="rounded-[12px] border border-[var(--agent-border)] bg-white px-3 py-2.5 text-[13px] font-medium text-[#4E5968] active:bg-[#F2F4F6]"
            >
              {action.label || action}
            </button>
          ))}
        </section>
      )}
    </>
  );
}
