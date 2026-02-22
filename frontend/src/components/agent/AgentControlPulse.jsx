export default function AgentControlPulse({ active = false, children }) {
  return (
    <div
      className={`transition-all duration-300 ${
        active
          ? 'rounded-[16px] shadow-[0_0_0_1px_rgba(255,107,0,0.14),0_0_24px_rgba(255,107,0,0.22)] animate-agent-control-pulse'
          : ''
      }`}
    >
      {children}
    </div>
  );
}
