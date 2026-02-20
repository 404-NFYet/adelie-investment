const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

function pad2(value) {
  return String(value).padStart(2, '0');
}

function toKstVirtualDate(input = new Date()) {
  const date = input instanceof Date ? input : new Date(input);
  return new Date(date.getTime() + KST_OFFSET_MS);
}

export function getKstDateParts(input = new Date()) {
  const virtual = toKstVirtualDate(input);
  return {
    year: virtual.getUTCFullYear(),
    month: virtual.getUTCMonth() + 1,
    day: virtual.getUTCDate(),
    weekday: virtual.getUTCDay(),
  };
}

export function formatDateKeyFromParts({ year, month, day }) {
  return `${year}-${pad2(month)}-${pad2(day)}`;
}

export function formatDateKeyKST(input = new Date()) {
  return formatDateKeyFromParts(getKstDateParts(input));
}

export function getKstTodayDateKey() {
  return formatDateKeyKST(new Date());
}

export function formatTimeKST(input) {
  if (!input) return '';
  const virtual = toKstVirtualDate(input);
  return `${pad2(virtual.getUTCHours())}:${pad2(virtual.getUTCMinutes())}`;
}

export function formatDateDisplayFromKey(dateKey) {
  const [year, month, day] = String(dateKey || '').split('-').map(Number);
  if (!year || !month || !day) return '';
  return `${year}.${pad2(month)}.${pad2(day)}`;
}

export function getKstWeekDays(input = new Date()) {
  const todayParts = getKstDateParts(input);
  const todayKey = formatDateKeyFromParts(todayParts);

  const todayVirtual = new Date(Date.UTC(todayParts.year, todayParts.month - 1, todayParts.day));
  const diffToMonday = (todayParts.weekday + 6) % 7;
  const mondayVirtual = new Date(todayVirtual);
  mondayVirtual.setUTCDate(todayVirtual.getUTCDate() - diffToMonday);

  return Array.from({ length: 7 }, (_, index) => {
    const current = new Date(mondayVirtual);
    current.setUTCDate(mondayVirtual.getUTCDate() + index);

    const year = current.getUTCFullYear();
    const month = current.getUTCMonth() + 1;
    const day = current.getUTCDate();
    const weekday = current.getUTCDay();
    const dateKey = formatDateKeyFromParts({ year, month, day });

    return {
      dateKey,
      year,
      month,
      day,
      weekday,
      label: WEEKDAY_LABELS[weekday],
      isToday: dateKey === todayKey,
    };
  });
}

export function shiftYearMonth(year, month, delta) {
  const value = new Date(Date.UTC(year, month - 1 + delta, 1));
  return {
    year: value.getUTCFullYear(),
    month: value.getUTCMonth() + 1,
  };
}

export function buildKstMonthGrid(year, month) {
  const firstDay = new Date(Date.UTC(year, month - 1, 1));
  const firstWeekday = firstDay.getUTCDay();
  const start = new Date(firstDay);
  start.setUTCDate(firstDay.getUTCDate() - firstWeekday);

  return Array.from({ length: 42 }, (_, index) => {
    const current = new Date(start);
    current.setUTCDate(start.getUTCDate() + index);

    const cellYear = current.getUTCFullYear();
    const cellMonth = current.getUTCMonth() + 1;
    const cellDay = current.getUTCDate();

    return {
      dateKey: formatDateKeyFromParts({ year: cellYear, month: cellMonth, day: cellDay }),
      year: cellYear,
      month: cellMonth,
      day: cellDay,
      weekday: current.getUTCDay(),
      isCurrentMonth: cellMonth === month,
    };
  });
}
