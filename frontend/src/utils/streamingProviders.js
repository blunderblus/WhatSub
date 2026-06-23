const TYPE_ORDER = {
  subscription: 10,
  free: 20,
  ads: 30,
  rent: 40,
  buy: 50,
};

function normalizeProviderKey(provider) {
  const service = provider?.service || '';
  const displayName = provider?.display_name || '';
  const iconUrl = provider?.icon_url || '';
  return [service, displayName, iconUrl].find((value) => value.trim())?.trim().toLowerCase() || '';
}

function sortByType(providers) {
  return [...providers].sort((a, b) => {
    const left = TYPE_ORDER[a.type] ?? 999;
    const right = TYPE_ORDER[b.type] ?? 999;
    return left - right;
  });
}

function uniqueValues(values) {
  return values.filter((value, index, source) => value && source.indexOf(value) === index);
}

function buildProviderGroup(providers) {
  const orderedProviders = sortByType(providers);
  const mainProvider = orderedProviders.find((provider) => provider.icon_url) || orderedProviders[0] || {};
  const linkedProvider = orderedProviders.find((provider) => (provider.link || '').trim());
  const typeLabels = uniqueValues(orderedProviders.map((provider) => provider.type_label || provider.type));
  const expiresOnList = uniqueValues(orderedProviders.map((provider) => provider.expires_on));

  return {
    ...mainProvider,
    key: normalizeProviderKey(mainProvider),
    link: linkedProvider?.link || mainProvider.link || '',
    variants: orderedProviders,
    typeLabels,
    expiresOnList,
  };
}

export function groupProvidersByPlatform(providers) {
  const grouped = new Map();

  providers.forEach((provider) => {
    const key = normalizeProviderKey(provider);
    if (!key) return;
    const providersForKey = grouped.get(key) || [];
    providersForKey.push(provider);
    grouped.set(key, providersForKey);
  });

  return Array.from(grouped.values()).map(buildProviderGroup);
}

export function uniqueProvidersByPlatform(providers) {
  return groupProvidersByPlatform(providers);
}

export function formatProviderTypes(providerGroup) {
  return (providerGroup.typeLabels || []).join(' · ');
}
