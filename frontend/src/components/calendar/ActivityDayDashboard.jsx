import { useMemo } from 'react';
import { formatDateDisplayFromKey } from '../../utils/kstDate';

function getHourFromItem(item) {
  const fromLabel = Number(String(item?.timeLabel || '').split(':')[0]);
  if (Number.isFinite(fromLabel)) return fromLabel;

  const parsed = new Date(item?.occurredAt || Date.now());
  if (!Number.isNaN(parsed.getTime())) return parsed.getHours();

  return 0;
}

function buildSlotStats(items) {
  const slots = [
    { id: 'morning', label: '오전', range: '00:00-11:59', count: 0 },
    { id: 'afternoon', label: '오후', range: '12:00-17:59', count: 0 },
    { id: 'evening', label: '저녁', range: '18:00-23:59', count: 0 },
  ];

  for (const item of items) {
    const hour = getHourFromItem(item);
    if (hour < 12) slots[0].count += 1;
    else if (hour < 18) slots[1].count += 1;
    else slots[2].count += 1;
  }

  const max = Math.max(...slots.map((slot) => slot.count), 1);
  return slots.map((slot) => ({
    ...slot,
    percent: slot.count === 0 ? 0 : Math.round((slot.count / max) * 100),
  }));
}

function SummaryCard({ label, value, tone = 'neutral', onClick }) {
  const toneClass = tone === 'trade'
    ? 'text-[#c2410c]'
    : tone === 'learning'
      ? 'text-[#1d4ed8]'
      : 'text-[#101828]';

  if (!onClick) {
    return (
      <article className="rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-3">
        <p className="text-[11px] font-semibold text-[#99a1af]">{label}</p>
        <p className={`mt-1 text-lg font-extrabold ${toneClass}`}>{value}</p>
      </article>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-3 text-left transition hover:border-[#ffcfb7] hover:bg-[#fff7f2]"
    >
      <p className="text-[11px] font-semibold text-[#99a1af]">{label}</p>
      <p className={`mt-1 text-lg font-extrabold ${toneClass}`}>{value}</p>
      <p className="mt-1 text-[11px] font-semibold text-[#c2410c]">요약 카드 보기 ›</p>
    </button>
  );
}

function DashboardSkeleton({ dateKey }) {
  return (
    <section className="rounded-[24px] border border-border bg-white p-4 shadow-card sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-bold text-[#101828]">{formatDateDisplayFromKey(dateKey)} 활동 대시보드</h4>
        <span className="text-xs font-semibold text-[#99a1af]">로딩중</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="h-20 animate-pulse rounded-xl bg-[#f3f4f6]" />
        <div className="h-20 animate-pulse rounded-xl bg-[#f3f4f6]" />
        <div className="h-20 animate-pulse rounded-xl bg-[#f3f4f6]" />
        <div className="h-20 animate-pulse rounded-xl bg-[#f3f4f6]" />
      </div>
    </section>
  );
}

export default function ActivityDayDashboard({ dateKey, items, isLoading, error, onOpenArchive }) {
  const safeItems = Array.isArray(items) ? items : [];

  const stats = useMemo(() => {
    const trades = safeItems.filter((item) => item.type === 'trade');
    const learningItems = safeItems.filter((item) => item.type === 'learning');
    const buyCount = trades.filter((item) => item?.meta?.tradeType === 'buy').length;
    const sellCount = trades.filter((item) => item?.meta?.tradeType === 'sell').length;
    const dominantType = trades.length >= learningItems.length ? 'trade' : 'learning';

    return {
      total: safeItems.length,
      tradeCount: trades.length,
      learningCount: learningItems.length,
      buyCount,
      sellCount,
      dominantType,
      latestItem: safeItems[0] || null,
      slotStats: buildSlotStats(safeItems),
    };
  }, [safeItems]);

  if (isLoading) return <DashboardSkeleton dateKey={dateKey} />;

  if (error) {
    return (
      <section className="rounded-[24px] border border-border bg-white p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-sm font-bold text-[#101828]">{formatDateDisplayFromKey(dateKey)} 활동 대시보드</h4>
          <span className="text-xs font-semibold text-[#99a1af]">오류</span>
        </div>
        <div className="rounded-xl border border-[#fecaca] bg-[#fef2f2] px-4 py-6 text-sm text-[#b91c1c]">
          {error}
        </div>
      </section>
    );
  }

  if (safeItems.length === 0) {
    return (
      <section className="rounded-[24px] border border-border bg-white p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-sm font-bold text-[#101828]">{formatDateDisplayFromKey(dateKey)} 활동 대시보드</h4>
          <span className="text-xs font-semibold text-[#99a1af]">0건</span>
        </div>
        <div className="rounded-xl border border-border bg-[#f9fafb] px-4 py-6 text-sm text-text-secondary">
          선택한 날짜의 활동이 없습니다.
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-[24px] border border-border bg-white p-4 shadow-card sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-bold text-[#101828]">{formatDateDisplayFromKey(dateKey)} 활동 대시보드</h4>
        <span className="text-xs font-semibold text-[#99a1af]">{stats.total}건</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <SummaryCard label="총 활동" value={stats.total} />
        <SummaryCard
          label="학습"
          value={stats.learningCount}
          tone="learning"
          onClick={() => onOpenArchive?.({ kind: 'learning', tradeType: null, dateKey })}
        />
        <SummaryCard
          label="매수"
          value={stats.buyCount}
          tone="trade"
          onClick={() => onOpenArchive?.({ kind: 'trade', tradeType: 'buy', dateKey })}
        />
        <SummaryCard
          label="매도"
          value={stats.sellCount}
          tone="trade"
          onClick={() => onOpenArchive?.({ kind: 'trade', tradeType: 'sell', dateKey })}
        />
      </div>

      <article className="mt-3 rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-3">
        <p className="text-[11px] font-semibold text-[#99a1af]">시간대 분포</p>
        <div className="mt-3 space-y-2.5">
          {stats.slotStats.map((slot) => (
            <div key={slot.id}>
              <div className="mb-1 flex items-center justify-between text-[11px] text-[#6b7280]">
                <span>{slot.label} ({slot.range})</span>
                <span>{slot.count}건</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#eceff3]">
                <div
                  className="h-full rounded-full bg-[#ff9a72] transition-all"
                  style={{ width: `${slot.percent}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </article>

      <button
        type="button"
        onClick={() => onOpenArchive?.({ kind: stats.dominantType, tradeType: null, dateKey })}
        className="mt-3 w-full rounded-xl border border-[#eef2f7] bg-[#fcfcfd] px-3 py-3 text-left transition hover:border-[#ffcfb7] hover:bg-[#fff7f2]"
      >
        <p className="text-[11px] font-semibold text-[#99a1af]">오늘의 인사이트</p>
        <p className="mt-2 text-sm font-semibold text-[#101828]">
          최근 활동: {stats.latestItem?.title || '-'}
        </p>
        <p className="mt-1 text-xs text-[#6b7280]">
          {stats.latestItem?.subtitle || '상세 정보가 없습니다.'}
        </p>
        <div className="mt-3 flex items-center justify-between text-xs">
          <span className="font-medium text-[#6b7280]">
            집중 영역: {stats.dominantType === 'trade' ? '거래 중심' : '학습 중심'}
          </span>
          <span className="font-semibold text-[#c2410c]">이전 카드 모아보기 ›</span>
        </div>
      </button>
    </section>
  );
}
