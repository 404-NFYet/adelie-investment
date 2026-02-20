import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AppHeader from '../components/layout/AppHeader';
import useActivityFeed from '../hooks/useActivityFeed';
import { formatDateDisplayFromKey, getKstTodayDateKey, shiftDateKey } from '../utils/kstDate';

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
      ? 'bg-[#fee2e2] text-[#dc2626]'
      : 'bg-[#dbeafe] text-[#2563eb]'
    : 'bg-[#ffedd5] text-[#ea580c]';

  const rightLabel = isTrade ? '단가' : (item?.meta?.status === 'completed' ? '상태' : '진행률');
  const rightValue = isTrade
    ? (item?.meta?.price ? `${Number(item.meta.price).toLocaleString()}원` : '-')
    : (item?.meta?.status === 'completed' ? '완료' : `${item?.meta?.progressPercent || 0}%`);

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center rounded-2xl bg-white px-2 py-3 text-left transition hover:bg-gray-50 active:bg-gray-100"
    >
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${badgeClass}`}>
        {badgeText}
      </div>
      <div className="ml-3 min-w-0 flex-1">
        <h3 className="truncate text-[15px] font-bold text-[#101828]">
          {item.title}
        </h3>
        <p className="mt-0.5 truncate text-[13px] text-[#6b7280]">{item.subtitle}</p>
      </div>
      <div className="ml-3 flex shrink-0 flex-col items-end justify-center">
        <span className="text-[16px] font-bold text-[#101828]">{rightValue}</span>
        <span className="mt-0.5 text-[11px] font-medium text-[#99a1af]">{rightLabel}</span>
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
  const todayDateKey = getKstTodayDateKey();

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

  const title = getArchiveTitle(kind, tradeType);
  const canMoveToNewer = selectedDateKey < todayDateKey;
  const canMoveToOlder = true;

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-24">
      <AppHeader showBack title={title} />

      <main className="container space-y-4 py-4">
        <section className="flex items-center justify-between rounded-[24px] border border-border bg-white px-4 py-3 shadow-card">
          <button
            type="button"
            onClick={() => {
              if (!canMoveToOlder) return;
              const olderDate = shiftDateKey(selectedDateKey, -1);
              if (olderDate) {
                const newParams = new URLSearchParams(searchParams);
                newParams.set('date', olderDate);
                navigate(`?${newParams.toString()}`, { replace: true });
              }
            }}
            disabled={!canMoveToOlder}
            className={`flex h-10 w-10 items-center justify-center rounded-xl transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
              canMoveToOlder
                ? 'text-[#99a1af] hover:bg-gray-50 hover:text-[#101828]'
                : 'cursor-not-allowed text-[#d1d5db]'
            }`}
            aria-label="과거 날짜"
          >
            ‹
          </button>
          <div className="text-center">
            <h2 className="text-[17px] font-bold text-[#101828]">{formatDateDisplayFromKey(selectedDateKey)}</h2>
            <p className="mt-0.5 text-[11px] text-[#6b7280]">
              {kind === 'trade' ? '거래 아카이브' : '학습 아카이브'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              if (!canMoveToNewer) return;
              const newerDate = shiftDateKey(selectedDateKey, 1);
              if (newerDate) {
                const newParams = new URLSearchParams(searchParams);
                newParams.set('date', newerDate);
                navigate(`?${newParams.toString()}`, { replace: true });
              }
            }}
            disabled={!canMoveToNewer}
            className={`flex h-10 w-10 items-center justify-center rounded-xl transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
              canMoveToNewer
                ? 'text-[#99a1af] hover:bg-gray-50 hover:text-[#101828]'
                : 'cursor-not-allowed text-[#d1d5db]'
            }`}
            aria-label="오늘에 가까운 날짜"
          >
            ›
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

          </>
        ) : null}
      </main>
    </div>
  );
}
