import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../contexts';

export default function Landing() {
  const navigate = useNavigate();
  const { user, isLoading } = useUser();
  const isAuthenticated = !!user?.isAuthenticated;

  useEffect(() => {
    if (isLoading || !isAuthenticated) return undefined;
    const timer = setTimeout(() => {
      navigate('/home', { replace: true });
    }, 1000);
    return () => clearTimeout(timer);
  }, [isLoading, isAuthenticated, navigate]);

  return (
    <div className="min-h-screen bg-[#f5f5f5] flex flex-col overflow-hidden">
      <main className="flex-1 flex flex-col items-center pt-20">
        <p className="text-center text-[34px] leading-tight font-bold tracking-tight text-black">
          <span className="text-primary">쉽고 깊은</span>
          <br />
          금융 이야기
        </p>

        <h1 className="mt-6 text-[72px] leading-none font-black tracking-tight text-black">
          ADELIE
        </h1>

        <motion.img
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          src="/images/figma/landing-car.png"
          alt="Adelie landing"
          className="mt-4 w-[140%] max-w-none -ml-[18%]"
        />
      </main>

      <div className="px-6 pb-10">
        <button
          onClick={() => navigate(isAuthenticated ? '/home' : '/auth')}
          className="w-full py-4 rounded-2xl bg-primary text-white text-base font-bold active:scale-[0.99] transition-transform"
        >
          {isAuthenticated ? '홈으로 이동' : '시작하기'}
        </button>
      </div>
    </div>
  );
}
