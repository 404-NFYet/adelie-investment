/**
 * AuthPrompt.jsx - 게스트가 인증 필요 기능 접근 시 회원가입 유도 바텀시트
 */
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import PenguinMascot from './PenguinMascot';

export default function AuthPrompt({ isOpen, onClose }) {
  const navigate = useNavigate();

  const handleRegister = () => {
    onClose();
    navigate('/auth');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 z-50 flex items-end justify-center"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="bg-white dark:bg-gray-900 rounded-t-3xl w-full max-w-mobile p-6 pb-8"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="w-10 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-6" />

          <div className="text-center">
            <div className="mb-4">
              <PenguinMascot variant="welcome" size={80} />
            </div>

            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
              계정을 만들면 더 많은 기능을!
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 leading-relaxed">
              모의투자, 학습 기록, 맞춤 추천을 이용하려면<br />
              회원가입이 필요해요.
            </p>

            <button
              onClick={handleRegister}
              className="w-full py-3 rounded-xl font-semibold text-white bg-primary hover:bg-primary/90 transition-colors mb-3"
            >
              회원가입하기
            </button>
            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              나중에 할게요
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
