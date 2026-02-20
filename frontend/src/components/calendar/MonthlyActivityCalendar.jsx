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
    <section className="rounded-[28px] border border-border bg-white p-5 shadow-card sm:rounded-[32px] sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          className="h-8 w-8 rounded-xl border border-border text-text-secondary transition hover:text-text-primary"
          aria-label="이전 달"
        >
          ‹
        </button>
        <h3 className="text-[17px] font-bold text-[#101828]">{formatMonthLabel(year, month)}</h3>
        <button
          type="button"
          onClick={onNextMonth}
          className="h-8 w-8 rounded-xl border border-border text-text-secondary transition hover:text-text-primary"
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
              className={`relative flex h-10 items-center justify-center rounded-xl border text-sm font-semibold transition sm:h-11 ${
                isSelected
                  ? 'border-[#ff6900] bg-[#ff7648] text-white shadow-[0_10px_15px_rgba(255,118,72,0.2)]'
                  : cell.isCurrentMonth
                    ? isActive
                      ? 'border-[#ff6900] bg-white text-[#101828]'
                      : isToday
                        ? 'border-[#ff6900] bg-[#fff1e8] text-[#ff6900]'
                        : 'border-[#f3f4f6] bg-white text-[#101828]'
                    : 'border-transparent bg-transparent text-[#c1c8d2]'
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
