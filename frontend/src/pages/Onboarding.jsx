/**
 * Onboarding.jsx - Apple-like 풀스크린 스크롤 온보딩
 * 대형 타이포 + framer-motion 스크롤 트리거 + 난이도 선택
 */
import { useState, useEffect, useCallback, useRef } from 'react';
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

const DIFFICULTY_OPTIONS = [
  { value: DIFFICULTY_LEVELS.BEGINNER, label: '입문', desc: '주식 투자를 처음 시작해요' },
  { value: DIFFICULTY_LEVELS.ELEMENTARY, label: '초급', desc: '기본 용어는 알고 있어요' },
  { value: DIFFICULTY_LEVELS.INTERMEDIATE, label: '중급', desc: '투자 경험이 어느 정도 있어요' },
];

const VALUE_PROPS = [
  {
    icon: '📊',
    title: '과거에서 배우는 투자',
    desc: '역사적 사례를 스토리로 풀어내어\n현재 시장을 이해할 수 있어요',
  },
  {
    icon: '🤖',
    title: 'AI 튜터와 함께',
    desc: '모르는 용어, 궁금한 종목이 있으면\nAI에게 바로 물어보세요',
  },
  {
    icon: '💰',
    title: '모의투자로 연습',
    desc: '가상 자금으로 실전처럼 투자하고\n결과를 확인해보세요',
  },
];

export default function Onboarding() {
  const [selectedDifficulty, setSelectedDifficulty] = useState(null);
  const { settings, setDifficulty, completeOnboarding, loginAsGuest } = useUser();
  const navigate = useNavigate();

  useEffect(() => {
    if (settings.hasCompletedOnboarding) {
      navigate('/', { replace: true });
    }
  }, [settings.hasCompletedOnboarding, navigate]);

  const handleComplete = useCallback(() => {
    setDifficulty(selectedDifficulty || DIFFICULTY_LEVELS.BEGINNER);
    completeOnboarding();
    loginAsGuest();
    navigate('/', { replace: true });
  }, [selectedDifficulty, setDifficulty, completeOnboarding, loginAsGuest, navigate]);

  const handleSkip = () => {
    setDifficulty(DIFFICULTY_LEVELS.BEGINNER);
    completeOnboarding();
    loginAsGuest();
    navigate('/', { replace: true });
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
            역사는 반복된다,<br />투자도 마찬가지
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

        {/* 가치 제안 3포인트 */}
        <Section className="py-20">
          <h2 className="text-2xl font-bold text-text-primary mb-10 text-center">
            투자를 더 쉽게,<br />더 똑똑하게
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
                <span className="text-2xl mt-0.5">{item.icon}</span>
                <div>
                  <h3 className="text-base font-semibold text-text-primary mb-1">{item.title}</h3>
                  <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </Section>

        {/* 난이도 선택 + CTA */}
        <Section className="py-20">
          <h2 className="text-2xl font-bold text-text-primary mb-2">
            투자 경험을 알려주세요
          </h2>
          <p className="text-sm text-text-secondary mb-8">맞춤형 설명을 위해 선택해주세요</p>

          <div className="space-y-3 mb-10">
            {DIFFICULTY_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setSelectedDifficulty(opt.value)}
                className={`w-full p-5 rounded-2xl border text-left transition-all ${
                  selectedDifficulty === opt.value
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-surface hover:border-text-muted'
                }`}
              >
                <div className={`font-semibold text-sm ${selectedDifficulty === opt.value ? 'text-primary' : 'text-text-primary'}`}>
                  {opt.label}
                </div>
                <div className="text-xs text-text-secondary mt-0.5">{opt.desc}</div>
              </button>
            ))}
          </div>

          <button
            onClick={handleComplete}
            disabled={!selectedDifficulty}
            className={`w-full py-4 rounded-2xl font-semibold text-base transition-all ${
              selectedDifficulty
                ? 'bg-primary text-white hover:bg-primary-hover active:scale-[0.98]'
                : 'bg-surface text-text-muted border border-border cursor-not-allowed'
            }`}
          >
            시작하기
          </button>
        </Section>
      </div>
    </div>
  );
}
