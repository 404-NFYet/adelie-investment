/**
 * SplashScreen.jsx - 앱 로딩 시 브랜딩 스플래시 화면
 * 펭귄 3D 이미지 + 서비스 이름 + 태그라인 글자별 순차 등장 + 로딩 바
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const TAGLINE = '역사는 반복된다, 시장도 마찬가지';

export default function SplashScreen({ onComplete }) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShow(false);
      onComplete?.();
    }, 2800);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="fixed inset-0 bg-background flex flex-col items-center justify-center z-[100]"
        >
          {/* 펭귄 3D 이미지 */}
          <motion.img
            src="/images/penguin-3d.png"
            alt="Adelie Penguin"
            className="w-28 h-28 mb-6"
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          />

          {/* 서비스 이름 */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-2xl font-bold text-text-primary mb-3"
          >
            아델리에
          </motion.h1>

          {/* 태그라인 - 글자별 순차 등장 */}
          <div className="flex justify-center flex-wrap gap-0">
            {TAGLINE.split('').map((char, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.03, duration: 0.3 }}
                className="text-sm text-text-secondary"
              >
                {char === ' ' ? '\u00A0' : char}
              </motion.span>
            ))}
          </div>

          {/* 부제 */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2, duration: 0.5 }}
            className="text-xs text-text-muted mt-2"
          >
            AI 기반 금융 학습 플랫폼
          </motion.p>

          {/* 로딩 바 0→100% */}
          <div className="mt-8 w-48 h-1 bg-border rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-primary rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: '100%' }}
              transition={{ delay: 0.8, duration: 1.8, ease: 'easeInOut' }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
