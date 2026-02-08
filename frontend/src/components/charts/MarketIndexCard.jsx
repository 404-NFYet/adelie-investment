export default function MarketIndexCard({ data }) {
  if (!data?.kospi && !data?.kosdaq) return <div className="flex items-center justify-center h-full text-xs text-text-muted">시장 데이터 준비 중...</div>;
  const renderIndex = (name, idx) => {
    if (!idx) return null;
    const change = idx.close - idx.open;
    const changePct = idx.open ? ((change / idx.open) * 100).toFixed(2) : '0.00';
    const isUp = change >= 0;
    const color = isUp ? '#EF4444' : '#3B82F6';
    const arrow = isUp ? '▲' : '▼';
    const rangeTotal = idx.high - idx.low || 1;
    const closePos = ((idx.close - idx.low) / rangeTotal) * 100;
    return (
      <div className="flex-1 px-3">
        <div className="text-[10px] font-bold text-text-muted tracking-widest mb-1">{name}</div>
        <div className="text-lg font-bold text-text-primary">{idx.close?.toLocaleString(undefined,{minimumFractionDigits:1,maximumFractionDigits:1})}</div>
        <div className="text-xs font-semibold mt-0.5" style={{color}}>{arrow} {Math.abs(change).toFixed(1)} ({changePct}%)</div>
        <div className="mt-2 h-1.5 bg-border-light rounded-full relative">
          <div className="absolute h-1.5 rounded-full" style={{backgroundColor:color, width:`${closePos}%`}}/>
        </div>
        <div className="flex justify-between text-[8px] text-text-muted mt-0.5">
          <span>{idx.low?.toLocaleString()}</span><span>{idx.high?.toLocaleString()}</span>
        </div>
      </div>
    );
  };
  return (
    <div className="w-full h-full flex items-center justify-center">
      <div className="flex w-full max-w-sm">
        {renderIndex('KOSPI', data.kospi)}
        <div className="w-px bg-border-light"/>
        {renderIndex('KOSDAQ', data.kosdaq)}
      </div>
    </div>
  );
}
