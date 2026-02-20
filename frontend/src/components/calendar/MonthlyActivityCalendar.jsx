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
    <section className="rounded-[24px] bg-white p-5 shadow-sm sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={onPrevMonth}
          className="flex h-8 w-8 items-center justify-center rounded-xl text-text-secondary transition hover:bg-gray-50 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/45"
          aria-label="이전 달"
        >
          ‹
        </button>
        <h3 className="text-[17px] font-bold text-[#101828]">{formatMonthLabel(year, month)}</h3>
        <button
          type="button"
          onClick={onNextMonth}
          className="flex h-8 w-8 items-center justify-center rounded-xl text-text-secondary transition hover:bg-gray-50 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/45"
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
          const isCurrentMonth = cell.isCurrentMonth;

          let cellClass = 'bg-transparent text-[#c1c8d2]';
          if (isCurrentMonth) {
            if (isToday && isSelected) {
              cellClass = 'bg-primary text-white font-extrabold';
            } else if (isToday) {
              cellClass = 'bg-[#fff1e8] text-primary font-extrabold';
            } else if (isSelected) {
              cellClass = 'bg-[#f3f4f6] text-[#101828] font-bold';
            } else if (isActive) {
              cellClass = 'bg-[#fff7f2] font-extrabold text-[#101828]';
            } else {
              cellClass = 'bg-white text-[#101828]';
            }
          }

          return (
            <button
              key={cell.dateKey}
              type="button"
              onClick={() => onSelectDateKey(cell.dateKey)}
              className={`relative flex h-10 items-center justify-center rounded-xl text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6900]/40 sm:h-11 ${cellClass}`}
              aria-label={`${cell.year}년 ${cell.month}월 ${cell.day}일`}
            >
              <span>{cell.day}</span>
              {isToday && isCurrentMonth ? (
                <span className={`absolute bottom-1 h-1.5 w-1.5 rounded-full ${isSelected ? 'bg-white' : 'bg-primary'}`} />
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
