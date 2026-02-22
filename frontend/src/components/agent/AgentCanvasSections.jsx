export default function AgentCanvasSections({
  canvasState,
  onActionClick,
}) {
  const actions = Array.isArray(canvasState.actions) ? canvasState.actions : [];
  const showActions = actions.length > 0;

  if (canvasState.viewType === 'empty') {
    return (
      <section className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-5">
        <p className="text-[14px] leading-7 text-[#4a5565]">
          질문을 입력하면 현재 화면 맥락을 반영해 요약과 근거를 정리해드립니다.
        </p>
      </section>
    );
  }

  if (canvasState.viewType === 'plain') {
    return (
      <>
        <section className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-5">
          <div className="space-y-3">
            {canvasState.textBlocks.map((item, index) => (
              <p key={`${item.slice(0, 24)}-${index}`} className="text-[15px] leading-7 text-[#111827]">
                {item}
              </p>
            ))}
          </div>
        </section>

        {showActions && (
          <section className="grid grid-cols-2 gap-2.5">
            {actions.map((action) => (
              <button
                key={action.id || action.label}
                type="button"
                onClick={() => onActionClick(action)}
                className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] px-3 py-2.5 text-[13px] font-semibold text-[#4a5565] transition-colors hover:bg-[#f3f4f6]"
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
      <section className="rounded-2xl border border-[rgba(243,244,246,0.5)] bg-[#f2f4f6] px-4 py-4">
        <p className="mb-2 text-xs font-extrabold uppercase tracking-[0.08em] text-[#6a7282]">KEY POINT</p>
        <p className="text-[15px] font-bold leading-7 text-[#1e2939]">{canvasState.keyPoint}</p>
      </section>

      <section className="space-y-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 inline-block h-6 w-1.5 rounded-full bg-[#ff7648]" />
          <h2 className="text-[20px] font-extrabold leading-[1.35] tracking-[-0.02em] text-[#111827]">
            핵심 해석
          </h2>
        </div>

        <p className="text-[15px] leading-7 tracking-[-0.01em] text-[#4a5565]">
          {canvasState.explanation}
        </p>

        {canvasState.bullets.length > 0 && (
          <ul className="space-y-2 text-[14px] leading-7 tracking-[-0.01em] text-[#364153]">
            {canvasState.bullets.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-2">
                <span className="mt-[11px] h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[#d1d5dc]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}

        {canvasState.quote && (
          <blockquote className="border-l-4 border-[rgba(255,118,72,0.25)] pl-4 text-[14px] italic leading-7 text-[#6a7282]">
            {canvasState.quote}
          </blockquote>
        )}
      </section>

      {showActions && (
        <section className="grid grid-cols-2 gap-2.5">
          {actions.map((action) => (
            <button
              key={action.id || action.label}
              type="button"
              onClick={() => onActionClick(action)}
              className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] px-3 py-2.5 text-[13px] font-semibold text-[#4a5565] transition-colors hover:bg-[#f3f4f6]"
            >
              {action.label || action}
            </button>
          ))}
        </section>
      )}
    </>
  );
}
