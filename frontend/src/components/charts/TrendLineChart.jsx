import { motion } from 'framer-motion';

export default function TrendLineChart({ data }) {
  if (!data?.data_points?.length) return <div className="flex items-center justify-center h-full text-xs text-[#8B95A1]">데이터 준비 중...</div>;
  const pts = data.data_points;
  const unit = data.unit || '';
  const maxVal = Math.max(...pts.map(p => p.value)) * 1.15;
  const minVal = Math.min(...pts.map(p => p.value)) * 0.85;
  const range = maxVal - minVal || 1;
  const W = 340, H = 150, padL = 50, padR = 20, padT = 20, padB = 25;
  const cW = W - padL - padR, cH = H - padT - padB;
  const getX = (i) => padL + (i / Math.max(pts.length - 1, 1)) * cW;
  const getY = (v) => padT + cH - ((v - minVal) / range) * cH;
  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${getX(i)},${getY(p.value)}`).join(' ');
  const areaPath = linePath + ` L${getX(pts.length-1)},${H-padB} L${getX(0)},${H-padB} Z`;

  return (
    <div className="w-full h-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
        <text x="6" y={H/2} fontSize="8" fill="#8B95A1" textAnchor="middle" transform={`rotate(-90,8,${H/2})`}>{unit}</text>
        {[0,0.5,1].map((r,i)=>{const v=minVal+range*r;const y=getY(v);return(<g key={i}><line x1={padL} y1={y} x2={W-padR} y2={y} stroke="#F2F4F6" strokeWidth="1"/><text x={padL-4} y={y+3} fontSize="7" fill="#8B95A1" textAnchor="end">{Math.round(v)}</text></g>)})}
        <motion.path d={areaPath} fill="rgba(255,107,0,0.08)" initial={{opacity:0}} animate={{opacity:1}} transition={{duration:0.8}}/>
        <motion.path d={linePath} fill="none" stroke="#FF6B00" strokeWidth="2.5" strokeLinecap="round" initial={{pathLength:0}} animate={{pathLength:1}} transition={{duration:1}}/>
        {pts.map((p,i) => (
          <g key={i}>
            <motion.circle cx={getX(i)} cy={getY(p.value)} r="4" fill="#FF6B00" stroke="white" strokeWidth="2" initial={{scale:0}} animate={{scale:1}} transition={{delay:0.5+i*0.1}}/>
            <text x={getX(i)} y={getY(p.value)-10} fontSize="9" fill="#4E5968" textAnchor="middle" fontWeight="bold">{p.value.toLocaleString()}</text>
            <text x={getX(i)} y={H-padB+14} fontSize="8" fill="#8B95A1" textAnchor="middle">{p.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
