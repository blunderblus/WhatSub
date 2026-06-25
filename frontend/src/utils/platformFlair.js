const FLAIR_THEMES = {
  netflix: { bg: '#E50914', text: '#FFFFFF', ring: '#FF5A63' },
  'disney+': { bg: '#0B1957', text: '#FFFFFF', ring: '#3B82F6' },
  'apple tv+': { bg: '#1D1D1F', text: '#F5F5F7', ring: '#A1A1A6' },
  tving: { bg: '#FF153C', text: '#FFFFFF', ring: '#FF6B84' },
  wavve: { bg: '#0050FF', text: '#FFFFFF', ring: '#5C8FFF' },
  watcha: { bg: '#FF0558', text: '#FFFFFF', ring: '#FF5C94' },
  'amazon prime video': { bg: '#00A8E1', text: '#001F29', ring: '#7DD3FC' },
  'prime video': { bg: '#00A8E1', text: '#001F29', ring: '#7DD3FC' },
  'coupang play': { bg: '#0074E9', text: '#FFFFFF', ring: '#60A5FA' },
  spotv: { bg: '#111827', text: '#FFFFFF', ring: '#6B7280' },
  'icloud+': { bg: '#007AFF', text: '#FFFFFF', ring: '#60A5FA' },
  other: { bg: '#475569', text: '#F8FAFC', ring: '#94A3B8' },
  notice: { bg: '#B45309', text: '#FFFBEB', ring: '#FBBF24' },
  none: { bg: 'rgba(255, 255, 255, 0.05)', text: '#94A3B8', ring: '#64748B' },
};

function normalizePlatformName(name) {
  return String(name || '').trim().toLowerCase();
}

const FLAIR_SHORT_LABELS = {
  'amazon prime video': 'Prime',
  'prime video': 'Prime',
  'apple tv+': 'Apple TV+',
  'coupang play': '쿠팡플레이',
  'disney+': 'Disney+',
};

export function flairDisplayLabel({
  platformName = '',
  flairTag = '',
  isNotice = false,
  label = '',
  compact = false,
} = {}) {
  if (label && !compact) return label;
  if (isNotice) return '공지';
  if (flairTag === 'other') return '기타';
  const full = label || platformName || '';
  if (!full) return '';
  if (!compact) return full;
  const key = normalizePlatformName(platformName || full);
  return FLAIR_SHORT_LABELS[key] || full;
}

export function flairFullLabel(props) {
  return flairDisplayLabel({ ...props, compact: false, label: props.label || '' });
}

export function flairTheme({ platformName, flairTag, isNotice = false } = {}) {
  if (isNotice) return FLAIR_THEMES.notice;
  if (flairTag === 'other') return FLAIR_THEMES.other;
  const key = normalizePlatformName(platformName);
  if (key && FLAIR_THEMES[key]) return FLAIR_THEMES[key];
  if (!key) return null;
  return {
    bg: '#334155',
    text: '#F8FAFC',
    ring: '#64748B',
  };
}

export function flairStyle(theme) {
  if (!theme) return {};
  return {
    '--flair-bg': theme.bg,
    '--flair-text': theme.text,
    '--flair-ring': theme.ring,
  };
}

export const FLAIR_OTHER = 'other';
export const FLAIR_NONE_THEME = FLAIR_THEMES.none;
