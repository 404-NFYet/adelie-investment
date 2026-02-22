function getTone(phase) {
  if (phase === 'answering') return 'answering';
  if (phase === 'notice') return 'thinking';
  if (phase === 'stopped') return 'idle';
  if (phase === 'thinking' || phase === 'tool_call') return 'thinking';
  if (phase === 'error') return 'error';
  return 'idle';
}

const TONE_CLASS = {
  idle: 'bg-[#D1D6DB]',
  thinking: 'bg-[#FF6B00] agent-dot-wave',
  answering: 'bg-[#22c55e] agent-dot-wave',
  error: 'bg-[#ef4444] agent-dot-blink',
};

export default function AgentStatusDots({ phase = 'idle', label = '', compact = false }) {
  const tone = getTone(phase);
  const toneClass = TONE_CLASS[tone];

  return (
    <div className="flex items-center gap-1 text-[11px] text-[#8B95A1]" aria-live="polite">
      <div className="flex items-center gap-0.5">
        {[0, 1, 2].map((index) => (
          <span
            key={`dot-${index}`}
            className={`h-1.5 w-1.5 rounded-full ${toneClass}`}
            style={tone === 'thinking' || tone === 'answering' ? { animationDelay: `${index * 0.18}s` } : undefined}
          />
        ))}
      </div>
      {!compact && <span className="truncate max-w-[10rem]">{label || '대기 중'}</span>}
    </div>
  );
}
