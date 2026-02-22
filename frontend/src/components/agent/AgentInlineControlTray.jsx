function statusColor(phase) {
  switch (phase) {
    case 'running':
      return 'text-[#FF6B00]';
    case 'success':
      return 'text-[#16a34a]';
    case 'error':
      return 'text-[#ef4444]';
    default:
      return 'text-[#B0B8C1]';
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
  const visibleActions = actions.slice(0, 2);

  return (
    <div className="pointer-events-auto mb-1 rounded-[14px] border border-[var(--agent-border,#E8EBED)] bg-white px-3 py-1.5 shadow-[var(--agent-shadow)]">
      {/* 요약 + 상태 1줄 */}
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 truncate text-[12px] font-medium text-[#333D4B]">{summary}</p>
        <span className={`flex-shrink-0 text-[10px] font-medium ${statusColor(controlState?.phase)}`}>
          {controlState?.phase === 'running' ? '실행 중' : ''}
        </span>
      </div>

      {/* 인라인 메시지 */}
      {hasInlineMessage && (
        <div className="mt-1 flex items-center justify-between gap-2">
          <p className="min-w-0 truncate text-[11px] text-[#6B7684]">{inlineMessage.text}</p>
          {inlineMessage.canvasPrompt && (
            <button
              type="button"
              onClick={() => onOpenCanvas?.(inlineMessage.canvasPrompt)}
              className="flex-shrink-0 text-[11px] font-medium text-[#FF6B00] active:opacity-70"
            >
              자세히
            </button>
          )}
        </div>
      )}

      {/* 액션칩 최대 2개 */}
      {visibleActions.length > 0 && (
        <div className="mt-1.5 flex gap-1.5">
          {visibleActions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onActionClick(action)}
              className="rounded-full border border-[var(--agent-border,#E8EBED)] bg-[#F7F8FA] px-2.5 py-1 text-[11px] font-medium text-[#4E5968] active:bg-[#E8EBED]"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
