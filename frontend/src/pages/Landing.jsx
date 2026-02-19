import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../contexts';

const LANDING_SLIDES = [
  {
    id: 'hero',
    type: 'hero',
    highlightTitle: '쉽고 깊은',
    subtitle: '금융 이야기',
    brand: 'ADELIE',
    image: '/images/figma/landing-car.png',
  },
  {
    id: 'habit',
    type: 'feature',
    title: ['하루 5분,', '금융 체력을 길러요'],
    body: [
      [{ text: '아델리와 함께라면' }],
      [{ text: '어려운 투자가 ' }, { text: '이야기', highlight: true }, { text: '처럼 쉬워져요.' }],
    ],
    image: '/images/figma/landing-penguin-book.png',
    imageClass: 'w-[228px] mt-6',
  },
  {
    id: 'case',
    type: 'feature',
    title: ['오늘 뜬 뉴스,', '옛날에도 있었을까?'],
    body: [
      [{ text: '현재 이슈를 ' }, { text: '과거 사례', highlight: true }, { text: '와 연결해' }],
      [{ text: '시장의 큰 흐름을 읽어드릴게요.' }],
    ],
    image: '/images/figma/landing-penguin-question.png',
    imageClass: 'w-[282px] mt-5',
  },
  {
    id: 'quiz',
    type: 'feature',
    title: ['눈으로만 보지 말고', '직접 결정해보세요'],
    body: [
      [{ text: '"나라면 이때 샀을까?"' }],
      [{ text: '모의 투자 퀴즈', highlight: true }, { text: '로 감각을 키워요.' }],
    ],
    image: '/images/figma/landing-penguin-magnifier.png',
    imageClass: 'w-[282px] mt-6',
  },
  {
    id: 'analyst',
    type: 'feature',
    title: ['투자 고민,', '이제 혼자 하지 마세요'],
    body: [
      [{ text: 'AI 애널리스트', highlight: true }, { text: '가 당신의 관점을' }],
      [{ text: '더 날카롭게 다듬어 드릴게요.' }],
    ],
    image: '/images/figma/landing-penguin-analyst.png',
    imageClass: 'w-[276px] mt-4',
  },
];

const SWIPE_THRESHOLD = 70;
const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 80 : -80,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction) => ({
    x: direction > 0 ? -80 : 80,
    opacity: 0,
  }),
};

export default function Landing() {
  const navigate = useNavigate();
  const { user, isLoading } = useUser();
  const isAuthenticated = !!user?.isAuthenticated;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const hasAutoAdvancedRef = useRef(false);

  const currentSlide = useMemo(() => LANDING_SLIDES[currentIndex], [currentIndex]);
  const totalSlides = LANDING_SLIDES.length;
  const featureSlides = LANDING_SLIDES.slice(1);
  const showControls = currentIndex > 0;
  const isLastSlide = currentIndex === totalSlides - 1;

  useEffect(() => {
    if (isLoading || !isAuthenticated) return undefined;
    const timer = setTimeout(() => {
      navigate('/home', { replace: true });
    }, 1000);
    return () => clearTimeout(timer);
  }, [isLoading, isAuthenticated, navigate]);

  useEffect(() => {
    LANDING_SLIDES.forEach((slide) => {
      const img = new Image();
      img.src = slide.image;
    });
  }, []);

  useEffect(() => {
    if (isLoading || isAuthenticated) return undefined;
    if (currentIndex !== 0 || hasAutoAdvancedRef.current) return undefined;

    const timer = setTimeout(() => {
      hasAutoAdvancedRef.current = true;
      setDirection(1);
      setCurrentIndex(1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [currentIndex, isAuthenticated, isLoading]);

  useEffect(() => {
    if (currentIndex > 0) {
      hasAutoAdvancedRef.current = true;
    }
  }, [currentIndex]);

  const goToSlide = (index, explicitDirection) => {
    const normalized = Math.max(0, Math.min(index, totalSlides - 1));
    if (normalized === currentIndex) return;
    const nextDirection = explicitDirection ?? (normalized > currentIndex ? 1 : -1);
    setDirection(nextDirection);
    setCurrentIndex(normalized);
  };

  // feature 슬라이드(index 1 이상)에서만 이전 가능
  const goPrev = () => {
    if (currentIndex <= 1) return;
    goToSlide(currentIndex - 1, -1);
  };

  // 마지막 슬라이드에서 순환 방지
  const goNext = () => {
    if (currentIndex >= totalSlides - 1) return;
    goToSlide(currentIndex + 1, 1);
  };

  const skipToLast = () => {
    goToSlide(totalSlides - 1, 1);
  };

  const handleDragEnd = (_, info) => {
    const offsetX = info?.offset?.x ?? 0;
    const velocityX = info?.velocity?.x ?? 0;

    if (offsetX <= -SWIPE_THRESHOLD || velocityX <= -500) {
      goNext();
      return;
    }

    if (offsetX >= SWIPE_THRESHOLD || velocityX >= 500) {
      goPrev();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <main className="relative mx-auto flex min-h-screen w-full max-w-[430px] flex-col overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.section
            key={currentSlide.id}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.12}
            onDragEnd={handleDragEnd}
            className="relative flex flex-1 flex-col touch-pan-y"
          >
            {!isLastSlide ? (
              <button
                type="button"
                onClick={skipToLast}
                aria-label="랜딩 건너뛰기"
                className="absolute right-4 top-5 z-20 rounded-full border border-white/40 bg-white/25 px-3 py-1.5 text-xs font-semibold text-black backdrop-blur-md transition hover:bg-white/35"
              >
                건너뛰기
              </button>
            ) : null}

            {currentSlide.type === 'hero' ? (
              <>
                <div className="pt-24 text-center">
                  <p className="text-[88px] leading-none font-black tracking-[-0.03em] text-black">
                    {currentSlide.brand}
                  </p>
                  <p className="mt-5 text-[24px] leading-tight text-black">
                    <span className="font-bold text-primary">{currentSlide.highlightTitle} </span>
                    {currentSlide.subtitle}
                  </p>
                </div>

                <img
                  src={currentSlide.image}
                  alt="ADELIE 랜딩 메인 비주얼"
                  className="pointer-events-none absolute bottom-[-58px] left-1/2 z-0 w-[170%] max-w-none -translate-x-[58%] select-none"
                />
              </>
            ) : (
              <>
                <section className="px-[37px] pt-[112px]">
                  <h1 className="line-limit-2 text-[clamp(2rem,8.2vw,2.35rem)] leading-[1.2] font-extrabold tracking-[-0.03em] whitespace-pre-wrap text-black">
                    {currentSlide.title[0]}
                    {'\n'}
                    {currentSlide.title[1]}
                  </h1>

                  <div className="mt-6 text-[20px] leading-[1.35] text-black">
                    {currentSlide.body.map((line, lineIdx) => (
                      <p key={`${currentSlide.id}-line-${lineIdx}`}>
                        {line.map((part, partIdx) => (
                          <span
                            key={`${currentSlide.id}-part-${lineIdx}-${partIdx}`}
                            className={part.highlight ? 'font-bold text-primary' : undefined}
                          >
                            {part.text}
                          </span>
                        ))}
                      </p>
                    ))}
                  </div>
                </section>

                <div className="flex flex-1 items-center justify-center px-10">
                  <img
                    src={currentSlide.image}
                    alt={`${currentSlide.title[0]} 비주얼`}
                    className={`pointer-events-none select-none ${currentSlide.imageClass}`}
                  />
                </div>
              </>
            )}

            {showControls ? (
              <>
                <footer className={`relative z-20 px-[41px] ${isLastSlide ? 'pb-[48px]' : 'pb-[24px]'}`}>
                  <div className={`flex justify-center gap-[10px] ${isLastSlide ? 'mb-[42px]' : ''}`}>
                    {featureSlides.map((slide, index) => {
                      const slideIndex = index + 1;
                      return (
                        <button
                          key={`landing-dot-${slide.id}`}
                          type="button"
                          onClick={() => goToSlide(slideIndex, slideIndex > currentIndex ? 1 : -1)}
                          className={`h-[15px] rounded-full transition-all ${
                            slideIndex === currentIndex ? 'w-[40px] bg-primary' : 'w-[15px] bg-[#d0d0d0]'
                          }`}
                          aria-label={`${index + 1}번째 랜딩 화면으로 이동`}
                          aria-current={slideIndex === currentIndex ? 'true' : undefined}
                        />
                      );
                    })}
                  </div>

                  {isLastSlide ? (
                    <button
                      type="button"
                      onClick={() => navigate('/auth')}
                      className="w-full rounded-[20px] bg-primary py-[16px] text-[24px] font-bold text-white transition-transform active:scale-[0.99]"
                    >
                      아델리 시작하기
                    </button>
                  ) : null}
                </footer>

                <button
                  type="button"
                  onClick={goPrev}
                  aria-label="이전 랜딩 화면"
                  className="absolute left-4 top-1/2 z-10 h-10 w-10 -translate-y-1/2 rounded-full border border-white/40 bg-white/25 text-black backdrop-blur-md transition hover:bg-white/35"
                >
                  <span className="text-lg leading-none">‹</span>
                </button>
                {!isLastSlide ? (
                  <button
                    type="button"
                    onClick={goNext}
                    aria-label="다음 랜딩 화면"
                    className="absolute right-4 top-1/2 z-10 h-10 w-10 -translate-y-1/2 rounded-full border border-white/40 bg-white/25 text-black backdrop-blur-md transition hover:bg-white/35"
                  >
                    <span className="text-lg leading-none">›</span>
                  </button>
                ) : null}
              </>
            ) : null}
          </motion.section>
        </AnimatePresence>
      </main>
    </div>
  );
}
