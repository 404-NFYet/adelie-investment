import { motion } from 'framer-motion';

export default function SingleBarChart({ data }) {
  if (!data?.data_points?.length) return <div className="flex items-center justify-center h-full text-xs text-[#8B95A1]">데이터 준비 중...</div>;
  const pts = data.data_points;
  const unit = data.unit || '';
  const maxVal = Math.max(...pts.map(p=>p.value))*1.2||1;
  const W=340,H=160,padL=45,padB=30,padT=10,cH=H-padT-padB;
  const barW=Math.min(45,(W-padL-20)/pts.length-10);

  return (
    <div className="w-full h-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
        <text x="4" y={H/2} fontSize="8" fill="#8B95A1" textAnchor="middle" transform={`rotate(-90,8,${H/2})`}>{unit}</text>
        <line x1={padL} y1={H-padB} x2={W-10} y2={H-padB} stroke="#F2F4F6" strokeWidth="1"/>
        {pts.map((p,i)=>{
          const h=(p.value/maxVal)*cH;
          const x=padL+i*((W-padL-20)/pts.length)+((W-padL-20)/pts.length-barW)/2;
          const y=H-padB-h;
          return(
            <g key={i}>
              <defs><linearGradient id={`sg${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#FF6B00"/><stop offset="100%" stopColor="#FFB280"/></linearGradient></defs>
              <motion.rect x={x} width={barW} rx="6" fill={`url(#sg${i})`} initial={{height:0,y:H-padB}} animate={{height:h,y}} transition={{duration:0.5,delay:i*0.08}}/>
              <text x={x+barW/2} y={y-5} fontSize="9" fill="#4E5968" textAnchor="middle" fontWeight="bold">{p.value.toLocaleString()}</text>
              <text x={x+barW/2} y={H-padB+14} fontSize="8" fill="#8B95A1" textAnchor="middle">{p.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
