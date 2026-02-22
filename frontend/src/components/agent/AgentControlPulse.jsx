export default function AgentControlPulse({ active = false, children }) {
  return (
    <div
      className={`transition-all duration-300 ${
        active
          ? 'rounded-[22px] bg-[radial-gradient(ellipse_at_top,rgba(255,118,72,0.22),rgba(255,118,72,0.04)_60%,transparent_80%)] shadow-[0_0_0_1px_rgba(255,118,72,0.15),0_0_22px_rgba(255,118,72,0.25)] animate-agent-control-pulse'
          : ''
      }`}
    >
      {children}
    </div>
  );
}
