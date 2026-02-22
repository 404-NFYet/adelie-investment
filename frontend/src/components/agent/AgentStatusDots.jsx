function getTone(phase) {
  if (phase === 'answering') return 'answering';
  if (phase === 'thinking' || phase === 'tool_call') return 'thinking';
  if (phase === 'error') return 'error';
  return 'idle';
}

const TONE_CLASS = {
  idle: 'bg-[#cfd4dc]',
  thinking: 'bg-[#f59e0b] agent-dot-wave',
  answering: 'bg-[#22c55e] agent-dot-wave',
  error: 'bg-[#ef4444] agent-dot-blink',
};

export default function AgentStatusDots({ phase = 'idle', label = '', compact = false }) {
  const tone = getTone(phase);
  const toneClass = TONE_CLASS[tone];

  return (
    <div className="flex items-center gap-1.5 text-xs text-[#6a7282]" aria-live="polite">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((index) => (
          <span
            key={`dot-${index}`}
            className={`h-2 w-2 rounded-full ${toneClass}`}
            style={tone === 'thinking' || tone === 'answering' ? { animationDelay: `${index * 0.18}s` } : undefined}
          />
        ))}
      </div>
      {!compact && <span className="truncate">{label || '대기 중'}</span>}
    </div>
  );
}
