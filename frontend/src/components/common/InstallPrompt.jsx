/**
 * InstallPrompt.jsx - PWA 설치 유도 배너
 * 모바일에서 "홈 화면에 추가" 유도
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // 이미 설치했거나 닫은 적 있으면 표시하지 않음
    if (localStorage.getItem('pwa-install-dismissed')) return;

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      // 3초 후 배너 표시 (즉시 표시하면 UX 방해)
      setTimeout(() => setShow(true), 3000);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      localStorage.setItem('pwa-install-dismissed', 'installed');
    }
    setDeferredPrompt(null);
    setShow(false);
  };

  const handleDismiss = () => {
    setDismissed(true);
    setShow(false);
    localStorage.setItem('pwa-install-dismissed', 'dismissed');
  };

  if (!show || dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="fixed bottom-20 left-4 right-4 bg-primary text-white rounded-2xl p-4 shadow-xl z-40 max-w-mobile mx-auto"
      >
        <div className="flex items-center gap-3">
          <span className="text-3xl">🐧</span>
          <div className="flex-1">
            <p className="font-bold text-sm">아델리에 앱 설치</p>
            <p className="text-xs opacity-80">홈 화면에 추가하면 더 빠르게!</p>
          </div>
          <button
            onClick={handleInstall}
            className="bg-white text-primary px-4 py-2 rounded-xl text-sm font-bold hover:bg-gray-100 transition-colors"
          >
            설치
          </button>
          <button
            onClick={handleDismiss}
            className="text-white/60 hover:text-white text-lg"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
