export default function AgentControlPulse({ active = false, children }) {
  return (
    <div
      className={`transition-all duration-300 ${
        active
          ? 'rounded-[20px] shadow-[0_-14px_28px_rgba(255,107,0,0.28),0_18px_36px_rgba(255,107,0,0.34)] animate-agent-control-pulse'
          : ''
      }`}
    >
      {children}
    </div>
  );
}
