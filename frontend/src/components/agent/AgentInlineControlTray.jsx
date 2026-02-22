function statusColor(phase) {
  switch (phase) {
    case 'running':
      return 'text-[#ff7648]';
    case 'success':
      return 'text-[#16a34a]';
    case 'error':
      return 'text-[#ef4444]';
    default:
      return 'text-[#6a7282]';
  }
}

export default function AgentInlineControlTray({
  summary,
  actions = [],
  controlState,
  inlineMessage,
  onOpenCanvas,
  onActionClick,
}) {
  const hasInlineMessage = Boolean(inlineMessage?.text);

  return (
    <div className="pointer-events-auto mb-1.5 rounded-[18px] border border-[#eceff3] bg-white px-3 py-2 shadow-[0_2px_10px_rgba(15,23,42,0.06)]">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[12px] font-semibold text-[#1f2937]">{summary}</p>
        {controlState?.phase === 'running' && (
          <span className="rounded-full bg-[#fff2eb] px-2 py-0.5 text-[10px] font-semibold text-[#ff7648]">
            Active
          </span>
        )}
      </div>

      {hasInlineMessage && (
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <p className="truncate text-[11px] text-[#4b5563]">{inlineMessage.text}</p>
          {inlineMessage.canvasPrompt && (
            <button
              type="button"
              onClick={() => onOpenCanvas?.(inlineMessage.canvasPrompt)}
              className="flex-shrink-0 rounded-full border border-[#eceff3] px-2 py-0.5 text-[10px] font-semibold text-[#364153] hover:bg-[#f7f9fb]"
            >
              캔버스 열기
            </button>
          )}
        </div>
      )}

      {actions.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onActionClick(action)}
              className="rounded-full border border-[#eceff3] bg-[#f7f9fb] px-2 py-0.5 text-[10px] font-semibold text-[#4a5565] transition-colors hover:bg-[#eef2f6]"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

      <p className={`mt-1.5 truncate text-[10px] font-medium ${statusColor(controlState?.phase)}`}>
        상태: {controlState?.text || '대기 중'}
      </p>
    </div>
  );
}
