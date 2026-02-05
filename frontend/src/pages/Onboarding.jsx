import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser, DIFFICULTY_LEVELS } from '../contexts';

const STEPS = [
  {
    id: 'welcome',
    content: (
      <>
        <motion.h1
          className="font-handwriting text-5xl text-primary mb-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          Narrative
        </motion.h1>
        <motion.p
          className="text-2xl font-bold text-text-primary mb-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          Investment
        </motion.p>
        <motion.p
          className="text-text-secondary"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          역사는 반복된다
        </motion.p>
      </>
    ),
  },
  {
    id: 'concept1',
    title: '과거에서 배우는 투자',
    description:
      '주식 시장의 역사적 사례를 통해 현재 상황을 이해하고, 더 나은 투자 결정을 내릴 수 있도록 도와드립니다.',
  },
  {
    id: 'concept2',
    title: '스토리텔링으로 쉽게',
    description:
      '복잡한 금융 용어와 차트 대신, 이해하기 쉬운 이야기로 투자의 핵심을 전달합니다.',
  },
  {
    id: 'concept3',
    title: 'AI 튜터와 함께',
    description:
      '궁금한 점이 있으시면 언제든 AI 튜터에게 물어보세요. 당신의 수준에 맞춰 설명해드립니다.',
  },
  {
    id: 'difficulty',
    title: '투자 경험을 알려주세요',
    description: '맞춤형 설명을 위해 현재 투자 경험 수준을 선택해주세요.',
    options: [
      {
        value: DIFFICULTY_LEVELS.BEGINNER,
        label: '입문',
        description: '주식 투자를 처음 시작해요',
      },
      {
        value: DIFFICULTY_LEVELS.ELEMENTARY,
        label: '초급',
        description: '기본 용어는 알고 있어요',
      },
      {
        value: DIFFICULTY_LEVELS.INTERMEDIATE,
        label: '중급',
        description: '투자 경험이 어느 정도 있어요',
      },
    ],
  },
];

export default function Onboarding() {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedDifficulty, setSelectedDifficulty] = useState(null);
  const { settings, setDifficulty, completeOnboarding } = useUser();
  const navigate = useNavigate();

  const step = STEPS[currentStep];
  const isLastStep = currentStep === STEPS.length - 1;
  const isFirstStep = currentStep === 0;

  // Navigate after onboarding is completed
  useEffect(() => {
    if (settings.hasCompletedOnboarding) {
      navigate('/auth', { replace: true });
    }
  }, [settings.hasCompletedOnboarding, navigate]);

  const handleNext = () => {
    if (isLastStep) {
      if (selectedDifficulty) {
        setDifficulty(selectedDifficulty);
        completeOnboarding();
        // Navigation will happen via useEffect when state updates
      }
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleSkip = () => {
    setDifficulty(DIFFICULTY_LEVELS.BEGINNER);
    completeOnboarding();
    // Navigation will happen via useEffect when state updates
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Skip button */}
      <div className="p-4 flex justify-end">
        <button
          onClick={handleSkip}
          className="text-text-secondary hover:text-text-primary text-sm"
        >
          건너뛰기
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-mobile mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="text-center w-full"
          >
            {step.content ? (
              step.content
            ) : (
              <>
                <h2 className="text-2xl font-bold text-text-primary mb-4">
                  {step.title}
                </h2>
                <p className="text-text-secondary mb-8">{step.description}</p>

                {/* Difficulty selection */}
                {step.options && (
                  <div className="space-y-3">
                    {step.options.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setSelectedDifficulty(option.value)}
                        className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
                          selectedDifficulty === option.value
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="font-bold text-text-primary">
                          {option.label}
                        </div>
                        <div className="text-sm text-text-secondary">
                          {option.description}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Progress & Navigation */}
      <div className="p-6 max-w-mobile mx-auto w-full">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-6">
          {STEPS.map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentStep ? 'bg-primary' : 'bg-border'
              }`}
            />
          ))}
        </div>

        {/* Navigation buttons */}
        <div className="flex gap-3">
          {!isFirstStep && (
            <button
              onClick={() => setCurrentStep((prev) => prev - 1)}
              className="flex-1 py-3 rounded-xl border border-border text-text-primary font-medium hover:bg-surface transition-colors"
            >
              이전
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={isLastStep && !selectedDifficulty}
            className={`flex-1 py-3 rounded-xl font-medium transition-colors ${
              isLastStep && !selectedDifficulty
                ? 'bg-border text-text-secondary cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary-hover'
            }`}
          >
            {isLastStep ? '시작하기' : '다음'}
          </button>
        </div>
      </div>
    </div>
  );
}
