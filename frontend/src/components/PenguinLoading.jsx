import { motion } from 'framer-motion';
import PenguinSVG from './PenguinSVG';

export default function PenguinLoading({ message = '분석 중이에요...' }) {
  return (
    <motion.div 
      className="flex flex-col items-center gap-3 py-2"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="flex items-end gap-0.5">
        {/* Lead penguin with wobble */}
        <div className="animate-wobble">
          <PenguinSVG size={26} />
        </div>
        <div className="w-3" />
        {/* 4 penguins with sequential bounce */}
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="animate-penguin-bounce" style={{ animationDelay: `${i * 120}ms` }}>
            <PenguinSVG size={22} />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-secondary">{message}</span>
        <div className="flex gap-0.5">
          {[0,1,2].map(i => (
            <span key={i} className="w-1 h-1 bg-primary rounded-full animate-bounce" style={{animationDelay: `${i*150}ms`}} />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
