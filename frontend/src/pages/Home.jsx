import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keywordsApi } from '../api';

const CARD_IMAGES = [
  '/images/figma/card-coin.png',
  '/images/figma/card-cash.png',
  '/images/figma/card-thumb.png',
];

export default function Home() {
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await keywordsApi.getToday();
        setKeywords(data.keywords || []);
      } catch (err) {
        setError('키워드를 불러오는데 실패했습니다.');
        setKeywords([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchKeywords();
  }, []);

  const visibleCards = useMemo(
    () =>
      [...keywords]
        .sort((a, b) => (b.case_id || 0) - (a.case_id || 0))
        .slice(0, 3),
    [keywords],
  );

  return (
    <div className="min-h-screen bg-background pb-24">
      <main className="max-w-mobile mx-auto px-6 pt-28">
        <p className="text-[16px] font-medium text-[#616161]">
          안녕하세요
        </p>

        <h1 className="line-limit-2 mt-2 text-[clamp(1.7rem,7.2vw,2.15rem)] leading-[1.22] font-black tracking-tight text-black break-keep">
          오늘 시장에서 놓치면 안 되는 <span className="text-primary">3가지 핵심 이야기</span>에요
        </h1>

        <section className="mt-8 space-y-4">
          {isLoading && (
            <div className="rounded-[20px] bg-white shadow-card border border-border px-6 py-10">
              <p className="text-sm text-text-secondary">키워드를 불러오는 중입니다...</p>
            </div>
          )}

          {!isLoading && error && (
            <div className="rounded-[20px] bg-white shadow-card border border-border px-6 py-10">
              <p className="text-sm text-red-500">{error}</p>
            </div>
          )}

          {!isLoading && !error && visibleCards.map((keyword, index) => (
            <article
              key={keyword.id || index}
              className="rounded-[20px] bg-white shadow-card border border-border px-6 py-5 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <h2 className="line-limit-2 text-[18px] leading-[1.3] font-bold text-black break-keep">
                  {keyword.title}
                </h2>
                <button
                  className="mt-4 px-5 h-[35px] rounded-[10px] bg-primary text-white text-sm font-semibold disabled:opacity-40"
                  disabled={!keyword.case_id}
                  onClick={() => navigate(`/narrative/${keyword.case_id}`, { state: { keyword } })}
                >
                  기사 읽으러 가기
                </button>
              </div>
              <img
                src={CARD_IMAGES[index] || CARD_IMAGES[0]}
                alt=""
                className="w-[96px] h-[96px] object-contain flex-shrink-0"
              />
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
