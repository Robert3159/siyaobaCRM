const UTC8_TIME_ZONE = 'Asia/Shanghai';
const DEFAULT_LOCALE = 'zh-CN';

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(DEFAULT_LOCALE, {
  timeZone: UTC8_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
});

function hasTimezoneInfo(value: string) {
  return /([zZ]|[+-]\d{2}:?\d{2})$/.test(value);
}

function normalizeDateInput(value: string) {
  let candidate = value.trim();
  if (!candidate) return '';
  candidate = candidate.replace(/\//g, '-');
  if (candidate.includes(' ') && !candidate.includes('T')) {
    candidate = candidate.replace(' ', 'T');
  }
  if (!hasTimezoneInfo(candidate)) {
    if (!candidate.includes('T')) {
      candidate = `${candidate}T00:00:00`;
    }
    candidate = `${candidate}Z`;
  }
  return candidate;
}

function toDate(value: unknown): Date | null {
  if (value === null || value === undefined || value === '') return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === 'number') {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (typeof value === 'string') {
    const normalized = normalizeDateInput(value);
    if (!normalized) return null;
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  return null;
}

export function formatUtc8DateTime(value: unknown, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback;
  const date = toDate(value);
  if (!date) return typeof value === 'string' ? value : fallback;
  return DATE_TIME_FORMATTER.format(date);
}
