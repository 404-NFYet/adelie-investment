/**
 * Onboarding.jsx - 스크롤 기반 온보딩
 * 섹션별 fade-in (IntersectionObserver) + 난이도 선택 + 시작
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser, DIFFICULTY_LEVELS } from '../contexts';

function useFadeIn() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.2 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return { ref, visible };
}

function FadeSection({ children, className = '', delay = 0 }) {
  const { ref, visible } = useFadeIn();
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${className}`}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(32px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

const DIFFICULTY_OPTIONS = [
  { value: DIFFICULTY_LEVELS.BEGINNER, label: '입문', desc: '주식 투자를 처음 시작해요' },
  { value: DIFFICULTY_LEVELS.ELEMENTARY, label: '초급', desc: '기본 용어는 알고 있어요' },
  { value: DIFFICULTY_LEVELS.INTERMEDIATE, label: '중급', desc: '투자 경험이 어느 정도 있어요' },
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
    <div className="min-h-screen bg-white">
      {/* 건너뛰기 */}
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md">
        <div className="max-w-mobile mx-auto px-6 py-3 flex justify-end">
          <button onClick={handleSkip} className="text-sm text-text-muted hover:text-text-secondary transition-colors">
            건너뛰기
          </button>
        </div>
      </div>

      <div className="max-w-mobile mx-auto px-6 pb-16">
        {/* 섹션 1: 로고 + 웰컴 */}
        <FadeSection className="pt-16 pb-20 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-text-primary mb-4">
            ADELIE
          </h1>
          <p className="text-lg text-text-secondary leading-relaxed">
            역사는 반복된다,<br />투자도 마찬가지
          </p>
        </FadeSection>

        {/* 섹션 2: 가치 제안 */}
        <FadeSection className="pb-20">
          <div className="space-y-6">
            {[
              {
                title: '과거에서 배우는 투자',
                desc: '역사적 사례를 스토리로 풀어내어\n현재 시장을 이해할 수 있어요',
              },
              {
                title: 'AI 튜터와 함께',
                desc: '모르는 용어, 궁금한 종목이 있으면\nAI에게 바로 물어보세요',
              },
              {
                title: '모의투자로 연습',
                desc: '가상 자금으로 실전처럼 투자하고\n결과를 확인해보세요',
              },
            ].map((item, i) => (
              <FadeSection key={i} delay={i * 120}>
                <div className="p-5 rounded-2xl bg-surface border border-border">
                  <h3 className="text-base font-semibold text-text-primary mb-1.5">{item.title}</h3>
                  <p className="text-sm text-text-secondary whitespace-pre-line leading-relaxed">{item.desc}</p>
                </div>
              </FadeSection>
            ))}
          </div>
        </FadeSection>

        {/* 섹션 3: 난이도 선택 + 시작 */}
        <FadeSection className="pb-20">
          <h2 className="text-xl font-bold text-text-primary mb-2">투자 경험을 알려주세요</h2>
          <p className="text-sm text-text-secondary mb-6">맞춤형 설명을 위해 선택해주세요</p>

          <div className="space-y-3 mb-8">
            {DIFFICULTY_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setSelectedDifficulty(opt.value)}
                className={`w-full p-4 rounded-2xl border text-left transition-all ${
                  selectedDifficulty === opt.value
                    ? 'border-primary bg-primary-light'
                    : 'border-border bg-surface-elevated hover:border-text-muted'
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
                ? 'bg-primary text-white hover:bg-primary-hover'
                : 'bg-surface text-text-muted border border-border cursor-not-allowed'
            }`}
          >
            시작하기
          </button>
        </FadeSection>
      </div>
    </div>
  );
}
