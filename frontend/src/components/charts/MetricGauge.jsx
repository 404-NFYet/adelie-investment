import { motion } from 'framer-motion';

export default function MetricGauge({ rate = 0, size = 120, label = '유사도' }) {
  const r = size / 2 - 8;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (rate / 100) * circumference;
  const color = rate >= 75 ? '#22C55E' : rate >= 50 ? '#FF6B00' : '#EF4444';

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" className="stroke-border-light" strokeWidth="6"/>
        <motion.circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} initial={{strokeDashoffset:circumference}} animate={{strokeDashoffset:offset}}
          transition={{duration:1,ease:'easeOut'}} transform={`rotate(-90 ${size/2} ${size/2})`}/>
        <text x={size/2} y={size/2+2} textAnchor="middle" fontSize="20" fontWeight="bold" className="fill-text-primary">{rate}%</text>
      </svg>
      <span className="text-xs text-text-muted mt-1 font-medium">{label}</span>
    </div>
  );
}
