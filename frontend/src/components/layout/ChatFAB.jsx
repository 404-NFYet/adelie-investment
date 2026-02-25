/**
 * ChatFAB.jsx - AI 튜터 플로팅 액션 버튼
 */
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTutor, useUser } from '../../contexts';

const HIDDEN_PREFIXES = ['/auth', '/landing', '/onboarding', '/tutor'];
const HIDDEN_EXACT = ['/'];

export default function ChatFAB() {
  const location = useLocation();
  const { isOpen, isLoading, openTutor, selectionCtaState, askTutorFromSelection } = useTutor();
  const { settings } = useUser();
  const isSelectionMode = selectionCtaState.active;

  const shouldHide =
    isOpen ||
    HIDDEN_EXACT.includes(location.pathname) ||
    HIDDEN_PREFIXES.some((prefix) => location.pathname.startsWith(prefix));

  if (shouldHide) return null;

  return (
    <div
      id="tutor-selection-btn"
      className={`fixed inset-x-0 z-50 pointer-events-none ${
        isSelectionMode
          ? 'bottom-[max(7rem,env(safe-area-inset-bottom))]'
          : 'bottom-[max(5.5rem,env(safe-area-inset-bottom))]'
      }`}
    >
      <div className="mx-auto w-full max-w-mobile px-4">
        <motion.div layout className="flex justify-end">
          <motion.button
            layout
            disabled={isSelectionMode && isLoading}
            onClick={() => {
              if (isSelectionMode) {
                askTutorFromSelection(settings?.difficulty || 'beginner');
                return;
              }
              openTutor();
            }}
            className={`pointer-events-auto flex items-center justify-center overflow-hidden bg-primary text-white shadow-lg transition-colors ${
              isSelectionMode
                ? 'h-12 w-full rounded-xl px-4 py-3 hover:bg-primary-hover active:bg-primary-active disabled:cursor-not-allowed disabled:opacity-70'
                : 'h-14 w-14 rounded-full active:scale-95'
            }`}
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32, mass: 0.85 }}
            aria-label={isSelectionMode ? '선택한 문구를 AI 튜터에게 질문' : 'AI 튜터 열기'}
          >
            <motion.div
              layout="position"
              className={`flex items-center ${isSelectionMode ? 'gap-1.5' : ''}`}
              transition={{ type: 'spring', stiffness: 420, damping: 32, mass: 0.85 }}
            >
              {isSelectionMode ? (
                <img src="/images/penguin-3d.png" alt="" className="h-4 w-4 rounded-full object-cover" />
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6">
                  <path d="M12 3.2l1.85 4.3 4.3 1.85-4.3 1.85L12 15.5l-1.85-4.3-4.3-1.85 4.3-1.85L12 3.2z" />
                  <path d="M18.6 14.1l.95 2.2 2.2.95-2.2.95-.95 2.2-.95-2.2-2.2-.95 2.2-.95.95-2.2z" />
                  <path d="M6.4 14.8l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6.6-1.4z" />
                </svg>
              )}

              <motion.span
                initial={false}
                animate={{
                  opacity: isSelectionMode ? 1 : 0,
                  width: isSelectionMode ? 'auto' : 0,
                  marginLeft: isSelectionMode ? 2 : 0,
                }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                className="whitespace-nowrap text-sm font-semibold"
              >
                AI 튜터에게 질문하기
              </motion.span>
            </motion.div>
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
}
