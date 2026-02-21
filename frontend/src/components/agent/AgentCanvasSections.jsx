export default function AgentCanvasSections({
  canvasState,
  contextPayload,
  onActionClick,
}) {
  return (
    <>
      <section className="rounded-[20px] border border-[rgba(243,244,246,0.5)] bg-[#f2f4f6] px-5 py-5">
        <p className="mb-2 text-xs font-extrabold uppercase tracking-[0.08em] text-[#6a7282]">KEY POINT</p>
        <p className="text-[17px] font-bold leading-8 text-[#1e2939]">{canvasState.keyPoint}</p>
      </section>

      <section className="space-y-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 inline-block h-6 w-1.5 rounded-full bg-[#ff7648]" />
          <h2 className="text-[30px] font-extrabold leading-[1.35] tracking-[-0.02em] text-[#111827]">
            왜 지금 이 포인트를 봐야 할까요?
          </h2>
        </div>

        <p className="text-[17px] leading-9 tracking-[-0.01em] text-[#4a5565]">
          {canvasState.explanation}
        </p>

        {canvasState.bullets.length > 0 && (
          <ul className="space-y-2 text-[15px] leading-7 tracking-[-0.01em] text-[#364153]">
            {canvasState.bullets.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-2">
                <span className="mt-[11px] h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[#d1d5dc]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}

        <blockquote className="border-l-4 border-[rgba(255,118,72,0.25)] pl-4 text-[15px] italic leading-8 text-[#6a7282]">
          {canvasState.quote}
        </blockquote>
      </section>

      <section className="grid grid-cols-2 gap-3">
        {canvasState.actions.map((action) => (
          <button
            key={action}
            type="button"
            onClick={() => onActionClick(action)}
            className="rounded-2xl border border-[#e5e7eb] bg-[#f9fafb] px-4 py-3 text-sm font-semibold text-[#4a5565] transition-colors hover:bg-[#f3f4f6]"
          >
            {action}
          </button>
        ))}
      </section>

      <section className="rounded-2xl border border-[#f3f4f6] bg-[#f9fafb] p-4">
        <h3 className="mb-2 text-sm font-bold text-[#364153]">AI가 보고 있는 것</h3>
        <p className="text-xs leading-5 text-[#6a7282]">모드: {canvasState.modeLabel}</p>
        {contextPayload?.stock_name && (
          <p className="text-xs leading-5 text-[#6a7282]">종목: {contextPayload.stock_name} ({contextPayload.stock_code})</p>
        )}
        {contextPayload?.has_holding !== undefined && (
          <p className="text-xs leading-5 text-[#6a7282]">
            보유 여부: {contextPayload.has_holding ? '보유 중' : '미보유'}
          </p>
        )}
        <p className="mt-2 text-xs leading-5 text-[#99a1af]">상태: {canvasState.aiStatus}</p>
      </section>
    </>
  );
}
