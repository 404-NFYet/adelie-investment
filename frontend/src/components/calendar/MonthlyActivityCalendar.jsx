import { buildKstMonthGrid, getKstTodayDateKey } from '../../utils/kstDate';

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

function formatMonthLabel(year, month) {
  return `${year}년 ${month}월`;
}

export default function MonthlyActivityCalendar({
  year,
  month,
  selectedDateKey,
  onSelectDateKey,
  onPrevMonth,
  onNextMonth,
  hasActivity,
}) {
  const todayKey = getKstTodayDateKey();
  const cells = buildKstMonthGrid(year, month);

  return (
    <section className="rounded-[28px] border border-[rgba(148,163,184,0.24)] bg-white p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_12px_24px_-18px_rgba(15,23,42,0.22)] sm:rounded-[32px] sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          className="h-8 w-8 rounded-xl border border-[rgba(148,163,184,0.35)] text-text-secondary shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6900]/45"
          aria-label="이전 달"
        >
          ‹
        </button>
        <h3 className="text-[17px] font-bold text-[#101828]">{formatMonthLabel(year, month)}</h3>
        <button
          type="button"
          onClick={onNextMonth}
          className="h-8 w-8 rounded-xl border border-[rgba(148,163,184,0.35)] text-text-secondary shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6900]/45"
          aria-label="다음 달"
        >
          ›
        </button>
      </div>

      <div className="mb-2 grid grid-cols-7 gap-1 text-center text-[11px] font-semibold text-[#99a1af] sm:gap-2">
        {WEEKDAY_LABELS.map((label) => (
          <div key={label}>{label}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1 sm:gap-2">
        {cells.map((cell) => {
          const isSelected = selectedDateKey === cell.dateKey;
          const isToday = todayKey === cell.dateKey;
          const isActive = hasActivity(cell.dateKey);

          return (
            <button
              key={cell.dateKey}
              type="button"
              onClick={() => onSelectDateKey(cell.dateKey)}
              className={`relative flex h-10 items-center justify-center rounded-xl text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6900]/40 sm:h-11 ${
                isSelected
                  ? 'bg-[#ff7648] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.3),0_10px_18px_rgba(255,118,72,0.22)]'
                  : cell.isCurrentMonth
                    ? isActive
                      ? 'bg-white text-[#101828] shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_4px_8px_rgba(15,23,42,0.06)]'
                      : isToday
                        ? 'bg-[#fff1e8] text-[#ff6900] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]'
                        : 'bg-white text-[#101828] shadow-[inset_0_1px_0_rgba(255,255,255,0.88),0_3px_7px_rgba(15,23,42,0.05)]'
                    : 'bg-transparent text-[#c1c8d2]'
              }`}
              aria-label={`${cell.year}년 ${cell.month}월 ${cell.day}일`}
            >
              <span>{cell.day}</span>
              {!isSelected && isActive && cell.isCurrentMonth ? (
                <span className="absolute bottom-1 h-1.5 w-1.5 rounded-full bg-[#ff6900]" />
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
