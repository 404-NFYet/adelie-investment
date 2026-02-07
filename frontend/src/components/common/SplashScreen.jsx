/**
 * SplashScreen.jsx - 앱 로딩 시 브랜딩 스플래시 화면
 * 아델리에 펭귄 로고 + 서비스 이름 + 태그라인 + 로딩 바
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PenguinMascot from './PenguinMascot';

export default function SplashScreen({ onComplete }) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShow(false);
      onComplete?.();
    }, 2500);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="fixed inset-0 bg-white dark:bg-gray-950 flex flex-col items-center justify-center z-[100]"
        >
          {/* 아델리에 펭귄 로고 */}
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            className="mb-8"
          >
            <PenguinMascot variant="welcome" size={120} />
          </motion.div>

          {/* 서비스 이름 */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-2xl font-bold text-gray-900 dark:text-white mb-2"
          >
            아델리에 투자
          </motion.h1>

          {/* 태그라인 */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="text-sm text-gray-500 dark:text-gray-400"
          >
            역사는 반복된다, 투자도 마찬가지
          </motion.p>

          {/* 로딩 바 */}
          <motion.div
            className="h-1 bg-primary rounded-full mt-8"
            initial={{ width: 0 }}
            animate={{ width: '60%' }}
            transition={{ delay: 0.8, duration: 1.5, ease: 'easeInOut' }}
            style={{ maxWidth: '200px' }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
