export function positivePageFromQuery(query) {
  const value = Array.isArray(query.page) ? query.page[0] : query.page;
  const page = Number.parseInt(value, 10);
  return Number.isFinite(page) && page > 0 ? page : 1;
}

export function selectedPlatformIdsFromQuery(query) {
  const single = query.platform_id;
  const multi = query.platform_ids;

  if (Array.isArray(single)) {
    return single.map(String);
  }
  if (single) {
    return [String(single)];
  }
  if (multi) {
    return String(multi).split(',').map((value) => value.trim()).filter(Boolean);
  }
  return [];
}

export function platformIdsToQuery(platformIds) {
  if (platformIds.length === 1) {
    return { platform_id: platformIds[0] };
  }
  if (platformIds.length > 1) {
    return { platform_ids: platformIds.join(',') };
  }
  return {};
}
