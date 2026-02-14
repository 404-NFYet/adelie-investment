import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../contexts';

const LANDING_SLIDES = [
  '/images/figma/landing-1.png',
  '/images/figma/landing-2.png',
  '/images/figma/landing-3.png',
  '/images/figma/landing-4.png',
  '/images/figma/landing-5.png',
];

const SLIDE_INTERVAL_MS = 3800;

export default function Landing() {
  const navigate = useNavigate();
  const { user, isLoading } = useUser();
  const isAuthenticated = !!user?.isAuthenticated;
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentSlide = useMemo(() => LANDING_SLIDES[currentIndex], [currentIndex]);

  useEffect(() => {
    if (isLoading || !isAuthenticated) return undefined;
    const timer = setTimeout(() => {
      navigate('/home', { replace: true });
    }, 1000);
    return () => clearTimeout(timer);
  }, [isLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (isLoading || isAuthenticated) return undefined;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % LANDING_SLIDES.length);
    }, SLIDE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [isLoading, isAuthenticated]);

  useEffect(() => {
    LANDING_SLIDES.forEach((src) => {
      const img = new Image();
      img.src = src;
    });
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0f172a]">
      <main className="absolute inset-0">
        <AnimatePresence mode="wait">
          <motion.img
            key={currentSlide}
            initial={{ opacity: 0, scale: 1.02 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.99 }}
            transition={{ duration: 0.65, ease: [0.33, 1, 0.68, 1] }}
            src={currentSlide}
            alt={`Adelie landing slide ${currentIndex + 1}`}
            className="h-full w-full object-cover"
          />
        </AnimatePresence>

        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/45 via-black/20 to-black/10" />
      </main>

      <div className="absolute inset-x-0 bottom-0 z-10 px-6 pb-10">
        <div className="mb-5 flex justify-center gap-2">
          {LANDING_SLIDES.map((_, index) => (
            <button
              key={`landing-dot-${index}`}
              type="button"
              onClick={() => setCurrentIndex(index)}
              className={`h-2.5 rounded-full transition-all ${
                index === currentIndex ? 'w-6 bg-white' : 'w-2.5 bg-white/45'
              }`}
              aria-label={`${index + 1}번째 랜딩 페이지로 이동`}
              aria-current={index === currentIndex ? 'true' : undefined}
            />
          ))}
        </div>
        <button
          onClick={() => navigate(isAuthenticated ? '/home' : '/auth')}
          className="w-full rounded-2xl bg-primary py-4 text-base font-bold text-white shadow-lg shadow-primary/30 transition-transform active:scale-[0.99]"
        >
          {isAuthenticated ? '홈으로 이동' : '시작하기'}
        </button>
      </div>
    </div>
  );
}
