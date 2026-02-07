/**
 * Onboarding.jsx - 3단계 자동 전환 온보딩
 * 리퀴드 글라스 효과 + 자동/스와이프 전환 + 난이도 선택 + 홈으로 이동
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser, DIFFICULTY_LEVELS } from '../contexts';
import PenguinMascot from '../components/common/PenguinMascot';

const AUTO_ADVANCE_MS = 3500;

const STEPS = [
  {
    id: 'welcome',
    auto: true,
    bg: 'from-orange-400 via-pink-400 to-purple-500',
  },
  {
    id: 'value',
    auto: true,
    title: '과거에서 배우는 투자, AI와 함께',
    desc: '역사적 사례를 스토리로 풀어내고\nAI 튜터가 맞춤 설명해드려요',
    bg: 'from-blue-400 via-indigo-400 to-purple-500',
  },
  {
    id: 'difficulty',
    auto: false,
    title: '투자 경험을 알려주세요',
    desc: '맞춤형 설명을 위해 선택해주세요',
    bg: 'from-emerald-400 via-teal-400 to-cyan-500',
  },
];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [selectedDifficulty, setSelectedDifficulty] = useState(null);
  const { settings, setDifficulty, completeOnboarding, loginAsGuest } = useUser();
  const navigate = useNavigate();

  // 이미 온보딩 완료했으면 홈으로
  useEffect(() => {
    if (settings.hasCompletedOnboarding) {
      navigate('/', { replace: true });
    }
  }, [settings.hasCompletedOnboarding, navigate]);

  // 자동 전환 (처음 2단계)
  useEffect(() => {
    if (STEPS[step]?.auto) {
      const timer = setTimeout(() => setStep(s => s + 1), AUTO_ADVANCE_MS);
      return () => clearTimeout(timer);
    }
  }, [step]);

  const handleComplete = useCallback(() => {
    if (selectedDifficulty) {
      setDifficulty(selectedDifficulty);
    } else {
      setDifficulty(DIFFICULTY_LEVELS.BEGINNER);
    }
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

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className={`min-h-screen bg-gradient-to-br ${current.bg} transition-all duration-1000 flex flex-col relative overflow-hidden`}>
      {/* 배경 블러 원 */}
      <div className="absolute top-[-20%] left-[-10%] w-[60vw] h-[60vw] bg-white/10 rounded-full blur-3xl" />
      <div className="absolute bottom-[-10%] right-[-15%] w-[50vw] h-[50vw] bg-white/10 rounded-full blur-3xl" />

      {/* 건너뛰기 */}
      <div className="p-4 flex justify-end relative z-10">
        <button onClick={handleSkip} className="text-white/60 hover:text-white text-sm transition-colors">
          건너뛰기
        </button>
      </div>

      {/* 콘텐츠 */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-mobile mx-auto relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
            className="text-center w-full"
          >
            {current.id === 'welcome' ? (
              <>
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2, duration: 0.6 }}
                  className="mb-8"
                >
                  <PenguinMascot variant="welcome" size={120} />
                </motion.div>
                <motion.h1
                  className="text-4xl font-bold text-white mb-3"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  아델리에 투자
                </motion.h1>
                <motion.p
                  className="text-white/80 text-lg"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 }}
                >
                  역사는 반복된다, 투자도 마찬가지
                </motion.p>
              </>
            ) : current.id === 'difficulty' ? (
              <div className="backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 shadow-2xl">
                <h2 className="text-2xl font-bold text-white mb-2">{current.title}</h2>
                <p className="text-white/70 mb-6 text-sm">{current.desc}</p>
                <div className="space-y-3">
                  {[
                    { value: DIFFICULTY_LEVELS.BEGINNER, label: '입문', desc: '주식 투자를 처음 시작해요' },
                    { value: DIFFICULTY_LEVELS.ELEMENTARY, label: '초급', desc: '기본 용어는 알고 있어요' },
                    { value: DIFFICULTY_LEVELS.INTERMEDIATE, label: '중급', desc: '투자 경험이 어느 정도 있어요' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setSelectedDifficulty(opt.value)}
                      className={`w-full p-4 rounded-2xl border-2 text-left transition-all backdrop-blur-xl ${
                        selectedDifficulty === opt.value
                          ? 'border-white bg-white/20'
                          : 'border-white/20 bg-white/5 hover:bg-white/10'
                      }`}
                    >
                      <div className="font-bold text-white">{opt.label}</div>
                      <div className="text-sm text-white/70">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="backdrop-blur-2xl bg-white/10 border border-white/20 rounded-3xl p-8 shadow-2xl">
                <div className="text-5xl mb-6">🐧</div>
                <h2 className="text-2xl font-bold text-white mb-3">{current.title}</h2>
                <p className="text-white/80 whitespace-pre-line leading-relaxed">{current.desc}</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* 하단 (프로그레스 + 버튼) */}
      <div className="p-6 max-w-mobile mx-auto w-full relative z-10">
        {/* 프로그레스 */}
        <div className="flex justify-center gap-2 mb-6">
          {STEPS.map((_, i) => (
            <div key={i} className="relative h-1 flex-1 max-w-[60px] rounded-full bg-white/20 overflow-hidden">
              {i < step && <div className="absolute inset-0 bg-white rounded-full" />}
              {i === step && STEPS[i].auto && (
                <motion.div
                  className="absolute inset-y-0 left-0 bg-white rounded-full"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: AUTO_ADVANCE_MS / 1000, ease: 'linear' }}
                />
              )}
              {i === step && !STEPS[i].auto && <div className="absolute inset-0 bg-white/50 rounded-full" />}
            </div>
          ))}
        </div>

        {/* 버튼 */}
        {isLast ? (
          <button
            onClick={handleComplete}
            className={`w-full py-4 rounded-2xl font-semibold text-lg transition-all ${
              selectedDifficulty
                ? 'bg-white text-gray-900 hover:bg-white/90 shadow-xl'
                : 'bg-white/20 text-white/50 cursor-not-allowed'
            }`}
            disabled={!selectedDifficulty}
          >
            시작하기
          </button>
        ) : (
          <button
            onClick={() => setStep(s => s + 1)}
            className="w-full py-4 rounded-2xl font-semibold text-lg bg-white/20 text-white hover:bg-white/30 transition-all backdrop-blur-xl"
          >
            다음
          </button>
        )}
      </div>
    </div>
  );
}
