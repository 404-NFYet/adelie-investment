import { useEffect, useMemo, useState } from 'react';
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

const SLIDE_INTERVAL_MS = 3800;
const FEATURE_SLIDES = LANDING_SLIDES.slice(1);

export default function Landing() {
  const navigate = useNavigate();
  const { user, isLoading } = useUser();
  const isAuthenticated = !!user?.isAuthenticated;
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentSlide = useMemo(() => LANDING_SLIDES[currentIndex], [currentIndex]);
  const activeFeatureIndex = currentIndex === 0 ? 0 : currentIndex - 1;

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
    LANDING_SLIDES.forEach((slide) => {
      const img = new Image();
      img.src = slide.image;
    });
  }, []);

  const moveToFeature = (index) => {
    setCurrentIndex(index + 1);
  };

  return (
    <div className="min-h-screen bg-[#f5f5f5]">
      <main className="relative mx-auto flex min-h-screen w-full max-w-[430px] flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.section
            key={currentSlide.id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -14 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="relative flex flex-1 flex-col"
          >
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
                  className="pointer-events-none absolute bottom-[-58px] left-1/2 w-[170%] max-w-none -translate-x-[58%] select-none"
                />
              </>
            ) : (
              <>
                <section className="px-[37px] pt-[112px]">
                  <h1 className="text-[40px] leading-[1.2] font-extrabold tracking-[-0.03em] whitespace-pre-wrap text-black">
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

                <footer className="px-[41px] pb-[48px]">
                  <div className="mb-[42px] flex justify-center gap-[10px]">
                    {FEATURE_SLIDES.map((_, index) => (
                      <button
                        key={`landing-dot-${index}`}
                        type="button"
                        onClick={() => moveToFeature(index)}
                        className={`h-[15px] rounded-full transition-all ${
                          index === activeFeatureIndex ? 'w-[40px] bg-primary' : 'w-[15px] bg-[#d0d0d0]'
                        }`}
                        aria-label={`${index + 1}번째 랜딩 화면으로 이동`}
                        aria-current={index === activeFeatureIndex ? 'true' : undefined}
                      />
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => navigate('/auth')}
                    className="w-full rounded-[20px] bg-primary py-[16px] text-[24px] font-bold text-white transition-transform active:scale-[0.99]"
                  >
                    아델리 시작하기
                  </button>
                </footer>
              </>
            )}
          </motion.section>
        </AnimatePresence>
      </main>
    </div>
  );
}
