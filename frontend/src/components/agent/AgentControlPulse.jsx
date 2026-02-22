export default function AgentControlPulse({ active = false, children }) {
  return (
    <div
      className={`transition-all duration-300 ${
        active
          ? 'rounded-[16px] shadow-[0_0_0_1px_rgba(255,107,0,0.2),0_0_30px_rgba(255,107,0,0.3)] animate-agent-control-pulse'
          : ''
      }`}
    >
      {children}
    </div>
  );
}
