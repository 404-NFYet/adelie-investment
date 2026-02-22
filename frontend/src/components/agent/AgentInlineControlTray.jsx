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
  onActionClick,
}) {
  return (
    <div className="pointer-events-auto mb-2 rounded-2xl border border-[rgba(255,118,72,0.18)] bg-[rgba(255,255,255,0.94)] px-3.5 py-2.5 shadow-[0_6px_24px_rgba(255,118,72,0.12)] backdrop-blur">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[11px] font-semibold text-[#364153]">{summary}</p>
        {controlState?.phase === 'running' && (
          <span className="rounded-md bg-[#fff0eb] px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.06em] text-[#ff7648]">
            Agent control active
          </span>
        )}
      </div>

      {actions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onActionClick(action)}
              className="rounded-full border border-[#f3f4f6] bg-[#f9fafb] px-2.5 py-1 text-[11px] font-semibold text-[#4a5565] transition-colors hover:bg-[#fff0eb] hover:text-[#ff7648]"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

      <p className={`mt-2 truncate text-[10px] font-semibold ${statusColor(controlState?.phase)}`}>
        상태: {controlState?.text || '대기 중'}
      </p>
    </div>
  );
}
