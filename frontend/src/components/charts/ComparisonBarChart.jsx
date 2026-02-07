import { motion } from 'framer-motion';

export default function ComparisonBarChart({ data }) {
  if (!data?.data_points?.length) return <div className="flex items-center justify-center h-full text-xs text-[#8B95A1]">데이터 준비 중...</div>;
  const pts = data.data_points;
  const unit = data.unit || '';
  const maxVal = Math.max(...pts.map(p => p.value)) * 1.2 || 1;
  const H = 150, padL = 45, padB = 28, padT = 10, cH = H - padT - padB;
  const barW = Math.min(48, 280 / pts.length - 12);
  const gap = barW * 0.3;
  const totalW = padL + pts.length * (barW + gap) + 30;

  return (
    <div className="w-full h-full">
      <svg viewBox={`0 0 ${totalW} ${H}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
        <text x="6" y={H/2} fontSize="8" fill="#8B95A1" textAnchor="middle" transform={`rotate(-90,8,${H/2})`}>{unit}</text>
        {[0,0.25,0.5,0.75,1].map((r,i) => {
          const val = Math.round(maxVal * r); const y = padT + cH - cH * r;
          return (<g key={i}><line x1={padL} y1={y} x2={totalW-10} y2={y} stroke="#F2F4F6" strokeWidth="1"/><text x={padL-5} y={y+3} fontSize="7" fill="#8B95A1" textAnchor="end">{val}</text></g>);
        })}
        {pts.map((p, i) => {
          const h = (p.value / maxVal) * cH;
          const x = padL + i * (barW + gap) + gap;
          const y = padT + cH - h;
          const color = p.color || (i % 2 === 0 ? '#ADB5BD' : '#FF6B00');
          return (
            <g key={i}>
              <motion.rect x={x} width={barW} rx="5" fill={color} initial={{height:0,y:padT+cH}} animate={{height:h,y}} transition={{duration:0.6,delay:i*0.1}}/>
              <text x={x+barW/2} y={y-6} fontSize="10" fill="#4E5968" textAnchor="middle" fontWeight="bold">{p.value.toLocaleString()}</text>
              <text x={x+barW/2} y={H-padB+14} fontSize="8" fill="#8B95A1" textAnchor="middle">{p.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
