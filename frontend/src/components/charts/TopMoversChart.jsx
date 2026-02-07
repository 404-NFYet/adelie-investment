export default function TopMoversChart({ data }) {
  if (!data?.gainers?.length && !data?.losers?.length) return <div className="flex items-center justify-center h-full text-xs text-text-muted">데이터 준비 중...</div>;
  const gainers = (data.gainers || []).slice(0, 3);
  const losers = (data.losers || []).slice(0, 3);
  const maxRate = Math.max(...[...gainers,...losers].map(s=>Math.abs(s.change_rate||0)), 1);
  const renderBar = (item, isGainer) => {
    const rate = item.change_rate || 0;
    const w = (Math.abs(rate)/maxRate)*100;
    const color = isGainer ? '#EF4444' : '#3B82F6';
    const sign = isGainer ? '+' : '';
    return (
      <div key={item.name} className="flex items-center gap-2 mb-1.5">
        <span className="text-[11px] text-text-secondary w-16 truncate text-right font-medium">{item.name}</span>
        <div className="flex-1 h-4 bg-border-light rounded-full relative overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{width:`${w}%`,backgroundColor:color}}/>
        </div>
        <span className="text-[11px] font-bold w-12" style={{color}}>{sign}{rate.toFixed(1)}%</span>
      </div>
    );
  };
  return (
    <div className="w-full h-full flex flex-col justify-center px-2">
      <div className="text-[9px] font-bold text-text-muted tracking-widest mb-2">급등</div>
      {gainers.map(g => renderBar(g, true))}
      <div className="h-px bg-border-light my-1.5"/>
      <div className="text-[9px] font-bold text-text-muted tracking-widest mb-2">급락</div>
      {losers.map(l => renderBar(l, false))}
    </div>
  );
}
