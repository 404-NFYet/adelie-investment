import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AppHeader from '../components/layout/AppHeader';
import useActivityFeed from '../hooks/useActivityFeed';
import { formatDateDisplayFromKey, getKstTodayDateKey } from '../utils/kstDate';

function parseDateKey(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ''))) return null;
  return value;
}

function getArchiveTitle(kind, tradeType) {
  if (kind === 'trade' && tradeType === 'buy') return '매수 카드 아카이브';
  if (kind === 'trade' && tradeType === 'sell') return '매도 카드 아카이브';
  if (kind === 'trade') return '거래 카드 아카이브';
  return '학습 카드 아카이브';
}

function ActivityCard({ item, onClick }) {
  const isTrade = item.type === 'trade';
  const tradeType = item?.meta?.tradeType;
  const badgeText = isTrade
    ? tradeType === 'buy'
      ? '매수'
      : tradeType === 'sell'
        ? '매도'
        : '거래'
    : '학습';
  const badgeClass = isTrade
    ? tradeType === 'buy'
      ? 'bg-[#fff4ed] text-[#c2410c]'
      : 'bg-[#eaf1ff] text-[#1d4ed8]'
    : 'bg-[#eaf1ff] text-[#1d4ed8]';

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-[20px] border border-border bg-white px-4 py-4 text-left shadow-card transition hover:border-[#ffcfb7] hover:bg-[#fffaf6]"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${badgeClass}`}>
            {badgeText}
          </span>
          <h3 className="mt-2 line-limit-2 text-[15px] font-bold leading-[1.35] text-[#101828] break-keep">
            {item.title}
          </h3>
          <p className="mt-1 text-xs text-[#6b7280]">{item.subtitle}</p>
        </div>
        <div className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-2xl bg-[#f3f4f6] text-center">
          <span className="text-[11px] font-semibold text-[#99a1af]">시간</span>
          <span className="mt-0.5 text-sm font-bold text-[#101828]">{item.timeLabel}</span>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="font-medium text-[#99a1af]">{formatDateDisplayFromKey(item.dateKey)}</span>
        <span className="font-semibold text-[#c2410c]">상세 보기 ›</span>
      </div>
    </button>
  );
}

export default function ActivityArchive() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { activities, isLoading, error } = useActivityFeed();

  const kind = searchParams.get('kind') === 'trade' ? 'trade' : 'learning';
  const tradeType = searchParams.get('tradeType') === 'buy' || searchParams.get('tradeType') === 'sell'
    ? searchParams.get('tradeType')
    : null;
  const selectedDateKey = parseDateKey(searchParams.get('date')) || getKstTodayDateKey();

  const filteredActivities = useMemo(() => {
    const source = Array.isArray(activities) ? activities : [];
    return source.filter((item) => {
      if (kind === 'trade' && item.type !== 'trade') return false;
      if (kind === 'learning' && item.type !== 'learning') return false;
      if (kind === 'trade' && tradeType && item?.meta?.tradeType !== tradeType) return false;
      return true;
    });
  }, [activities, kind, tradeType]);

  const selectedItems = useMemo(
    () => filteredActivities.filter((item) => item.dateKey === selectedDateKey),
    [filteredActivities, selectedDateKey],
  );

  const groupedPrevious = useMemo(() => {
    const map = new Map();
    for (const item of filteredActivities) {
      if (item.dateKey === selectedDateKey) continue;
      if (!map.has(item.dateKey)) map.set(item.dateKey, []);
      map.get(item.dateKey).push(item);
    }
    return Array.from(map.entries()).map(([dateKey, items]) => ({ dateKey, items }));
  }, [filteredActivities, selectedDateKey]);

  const title = getArchiveTitle(kind, tradeType);

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-24">
      <AppHeader showBack title={title} />

      <main className="container space-y-4 py-4">
        <section className="rounded-[24px] border border-border bg-white p-4 shadow-card">
          <p className="text-xs font-semibold text-[#99a1af]">기준 날짜</p>
          <h2 className="mt-1 text-[18px] font-extrabold text-[#101828]">{formatDateDisplayFromKey(selectedDateKey)}</h2>
          <p className="mt-1 text-xs text-[#6b7280]">
            {kind === 'trade' ? '거래 요약 카드' : '학습 요약 카드'}와 이전 기록을 한 번에 볼 수 있어요.
          </p>
          <button
            type="button"
            onClick={() => navigate(`/education?date=${selectedDateKey}`)}
            className="mt-3 h-9 rounded-xl border border-[#ffd7c2] bg-[#fff3eb] px-3 text-xs font-semibold text-[#c2410c]"
          >
            캘린더로 돌아가기
          </button>
        </section>

        {isLoading ? (
          <section className="rounded-[24px] border border-border bg-white p-4 shadow-card">
            <p className="text-sm text-text-secondary">아카이브를 불러오는 중입니다...</p>
          </section>
        ) : null}

        {!isLoading && error ? (
          <section className="rounded-[24px] border border-[#fecaca] bg-[#fef2f2] p-4">
            <p className="text-sm text-[#b91c1c]">{error}</p>
          </section>
        ) : null}

        {!isLoading && !error ? (
          <>
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-[18px] font-bold text-[#101828]">선택 날짜 요약 카드</h3>
                <span className="text-xs font-semibold text-[#99a1af]">{selectedItems.length}건</span>
              </div>
              {selectedItems.length === 0 ? (
                <div className="rounded-[20px] border border-border bg-white px-4 py-6 text-sm text-text-secondary">
                  선택 날짜에는 해당 카드가 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedItems.map((item) => (
                    <ActivityCard
                      key={item.id}
                      item={item}
                      onClick={() => {
                        if (item.type === 'learning') {
                          const caseId = Number(item?.meta?.contentId || 0);
                          if (Number.isInteger(caseId) && caseId > 0) navigate(`/narrative/${caseId}`);
                          else navigate('/history');
                          return;
                        }
                        navigate('/portfolio');
                      }}
                    />
                  ))}
                </div>
              )}
            </section>

            <section className="space-y-3 pb-2">
              <h3 className="text-[18px] font-bold text-[#101828]">이전 카드 모아보기</h3>
              {groupedPrevious.length === 0 ? (
                <div className="rounded-[20px] border border-border bg-white px-4 py-6 text-sm text-text-secondary">
                  이전 카드가 없습니다.
                </div>
              ) : (
                <div className="space-y-4">
                  {groupedPrevious.map((group) => (
                    <div key={group.dateKey} className="space-y-2">
                      <p className="text-xs font-semibold text-[#99a1af]">{formatDateDisplayFromKey(group.dateKey)}</p>
                      <div className="space-y-3">
                        {group.items.map((item) => (
                          <ActivityCard
                            key={item.id}
                            item={item}
                            onClick={() => {
                              if (item.type === 'learning') {
                                const caseId = Number(item?.meta?.contentId || 0);
                                if (Number.isInteger(caseId) && caseId > 0) navigate(`/narrative/${caseId}`);
                                else navigate('/history');
                                return;
                              }
                              navigate('/portfolio');
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
