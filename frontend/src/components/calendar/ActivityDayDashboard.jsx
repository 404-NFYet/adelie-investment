import { useMemo } from 'react';
import { formatDateDisplayFromKey } from '../../utils/kstDate';

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
          <span className="font-semibold text-[#c2410c]">해당일 기록 전체보기 ›</span>
        </div>
      </button>
    </section>
  );
}
