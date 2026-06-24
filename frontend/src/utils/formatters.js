const PROVIDER_DISPLAY_NAMES = {
  'google play movies': 'Google Play',
  'google play movies & tv': 'Google Play',
};

export function formatProviderName(provider) {
  const rawName = typeof provider === 'string' ? provider : provider?.display_name || provider?.service || '';
  const trimmedName = rawName.trim();
  return PROVIDER_DISPLAY_NAMES[trimmedName.toLowerCase()] || trimmedName;
}

export function providerInitial(name) {
  return (formatProviderName(name) || '?').charAt(0).toUpperCase();
}

export function formatCurrency(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}
