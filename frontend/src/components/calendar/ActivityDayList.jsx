import { formatDateDisplayFromKey } from '../../utils/kstDate';

function ActivityItem({ item }) {
  const badgeClass = item.type === 'trade'
    ? 'bg-[#fff4ed] text-[#c2410c]'
    : 'bg-[#eef4ff] text-[#1d4ed8]';
  const badgeText = item.type === 'trade' ? '거래' : '학습';

  return (
    <article className="rounded-2xl border border-border bg-white px-4 py-3 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#101828]">{item.title}</p>
          <p className="mt-1 text-xs text-[#6b7280]">{item.subtitle}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${badgeClass}`}>
            {badgeText}
          </span>
          <span className="text-[11px] text-[#99a1af]">{item.timeLabel}</span>
        </div>
      </div>
    </article>
  );
}

export default function ActivityDayList({ dateKey, items, isLoading, error }) {
  return (
    <section className="rounded-[24px] border border-border bg-[#f9fafb] p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-bold text-[#101828]">{formatDateDisplayFromKey(dateKey)} 활동 내역</h4>
        <span className="text-xs font-semibold text-[#99a1af]">{items.length}건</span>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-border bg-white px-4 py-6 text-sm text-text-secondary">
          활동 내역을 불러오는 중입니다...
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="rounded-xl border border-border bg-white px-4 py-6 text-sm text-red-500">
          {error}
        </div>
      ) : null}

      {!isLoading && !error && items.length === 0 ? (
        <div className="rounded-xl border border-border bg-white px-4 py-6 text-sm text-text-secondary">
          선택한 날짜의 활동이 없습니다.
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item) => (
            <ActivityItem key={item.id} item={item} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
