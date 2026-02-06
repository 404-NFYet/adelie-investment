import { motion } from 'framer-motion';

const VARIANTS = {
  welcome: { message: '안녕하세요! 무엇이든 물어보세요.', animate: 'bounce' },
  empty: { message: '아직 데이터가 없어요.', animate: 'none' },
  error: { message: '오류가 발생했어요.', animate: 'shake' },
  loading: { message: '준비 중이에요...', animate: 'pulse' },
};

export default function PenguinMascot({ variant = 'empty', message = null, action = null }) {
  const config = VARIANTS[variant] || VARIANTS.empty;
  const displayMessage = message || config.message;
  
  const animationClass = {
    bounce: 'animate-penguin-bounce',
    shake: 'animate-wobble',
    pulse: 'animate-pulse',
    none: '',
  }[config.animate];

  return (
    <div className="flex flex-col items-center py-6">
      <img 
        src="/images/penguin-3d.png" 
        alt="펭귄 마스코트" 
        className={`w-20 h-20 object-contain mb-3 ${animationClass}`}
      />
      <p className="text-sm text-text-secondary text-center">{displayMessage}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
