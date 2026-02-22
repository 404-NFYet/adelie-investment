export default function AgentControlPulse({ active = false, children }) {
  return (
    <div
      className={`transition-all duration-300 ${
        active
          ? 'rounded-[20px] bg-[radial-gradient(ellipse_at_top,rgba(255,118,72,0.12),rgba(255,118,72,0.02)_62%,transparent_82%)] shadow-[0_0_0_1px_rgba(255,118,72,0.12),0_0_14px_rgba(255,118,72,0.16)] animate-agent-control-pulse'
          : ''
      }`}
    >
      {children}
    </div>
  );
}
