/**
 * Onboarding.jsx - Apple-like 풀스크린 스크롤 온보딩
 * 대형 타이포 + framer-motion 스크롤 트리거
 */
import { useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { useUser, DIFFICULTY_LEVELS } from '../contexts';

function Section({ children, className = '' }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-10%' });

  return (
    <motion.section
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
      className={className}
    >
      {children}
    </motion.section>
  );
}

/* SVG 아이콘 */
const ChartIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);
const AIIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);
const PracticeIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
  </svg>
);

const VALUE_PROPS = [
  {
    icon: <ChartIcon />,
    title: '역사에서 배우는 금융 감각',
    desc: '과거 사례를 스토리로 풀어\n시장 흐름을 이해해요',
  },
  {
    icon: <AIIcon />,
    title: 'AI 튜터와 함께',
    desc: '모르는 용어, 궁금한 종목을\n바로 물어보세요',
  },
  {
    icon: <PracticeIcon />,
    title: '실전처럼 연습',
    desc: '가상 자금으로 매매를 연습하고\n결과를 확인해요',
  },
];

export default function Onboarding() {
  const { settings, setDifficulty, completeOnboarding } = useUser();
  const navigate = useNavigate();

  useEffect(() => {
    if (settings.hasCompletedOnboarding) {
      navigate('/', { replace: true });
    }
  }, [settings.hasCompletedOnboarding, navigate]);

  const handleComplete = useCallback(() => {
    setDifficulty(DIFFICULTY_LEVELS.BEGINNER);
    completeOnboarding();
    navigate('/auth', { replace: true });
  }, [setDifficulty, completeOnboarding, navigate]);

  const handleSkip = () => {
    completeOnboarding();
    navigate('/auth', { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 건너뛰기 */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
        <div className="max-w-mobile mx-auto px-6 py-3 flex justify-end">
          <button onClick={handleSkip} className="text-sm text-text-muted hover:text-text-secondary transition-colors">
            건너뛰기
          </button>
        </div>
      </div>

      <div className="max-w-mobile mx-auto px-6 pb-16">
        {/* Hero 섹션 - 펭귄 + 태그라인 */}
        <Section className="min-h-[70vh] flex flex-col items-center justify-center text-center">
          <motion.img
            src="/images/penguin-3d.png"
            alt="Adelie"
            className="w-32 h-32 mb-8"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
          />
          <h1 className="text-4xl font-bold tracking-tight text-text-primary mb-4">
            ADELIE
          </h1>
          <p className="text-xl text-text-secondary leading-relaxed">
            역사는 반복된다,<br />시장도 마찬가지
          </p>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1, duration: 0.8 }}
            className="mt-12 text-text-muted text-xs animate-bounce"
          >
            아래로 스크롤
          </motion.div>
        </Section>

        {/* 가치 제안 3포인트 + CTA */}
        <Section className="py-20">
          <h2 className="text-2xl font-bold text-text-primary mb-10 text-center">
            금융을 더 쉽게,<br />더 똑똑하게
          </h2>
          <div className="space-y-6">
            {VALUE_PROPS.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
                className="flex items-start gap-4 p-5 rounded-2xl bg-surface border border-border"
              >
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  {item.icon}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-text-primary mb-1">{item.title}</h3>
                  <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>

          <button
            onClick={handleComplete}
            className="w-full py-4 rounded-2xl font-semibold text-base bg-primary text-white hover:bg-primary-hover active:scale-[0.98] transition-all mt-10"
          >
            시작하기
          </button>
        </Section>
      </div>
    </div>
  );
}
