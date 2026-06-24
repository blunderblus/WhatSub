export function normalizeMonthlyAmount(amount, billingPeriod) {
  const price = Number(amount || 0);
  if (billingPeriod === 'annual') return Math.round(price / 12);
  if (billingPeriod === 'weekly') return Math.round((price * 52) / 12);
  return price;
}

export function planMonthlyPrice(plan) {
  return normalizeMonthlyAmount(plan?.price, plan?.billing_period);
}

export function subscriptionMonthlyAmount(subscription) {
  if (subscription?.monthly_amount != null) return Number(subscription.monthly_amount || 0);
  return normalizeMonthlyAmount(subscription?.payment_amount, subscription?.billing_cycle);
}

export function subscriptionsMonthlyTotal(subscriptions) {
  return (subscriptions || []).reduce((sum, subscription) => (
    sum + subscriptionMonthlyAmount(subscription)
  ), 0);
}

export function billingLabel(period) {
  if (period === 'annual') return '연간';
  if (period === 'weekly') return '주간';
  return '월간';
}

export function formatWon(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function monthKeyFromDate(date) {
  if (typeof date === 'string' && date.length >= 7) {
    return date.slice(0, 7);
  }
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function addMonthsToKey(key, delta) {
  const [year, month] = key.split('-').map(Number);
  const d = new Date(year, month - 1 + delta, 1);
  return monthKeyFromKeyDate(d);
}

function monthKeyFromKeyDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

function formatMonthLabel(key) {
  const [year, month] = key.split('-');
  return `${Number(year)}.${Number(month)}`;
}

function formatDayLabel(dateStr) {
  const day = Number(dateStr.slice(8, 10));
  return String(day);
}

function formatWeekLabel(startDay, endDay) {
  return `${startDay}~${endDay}일`;
}

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function toDateStr(year, month, day) {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function todayDateStr(referenceDate = new Date()) {
  const d = referenceDate instanceof Date ? referenceDate : new Date(referenceDate);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function aggregatePayments(items) {
  return (items || []).map((item) => ({
    platform_name: item.platform_name,
    amount: Number(item.amount || 0),
  }));
}

/**
 * Aggregate schedule items into monthly payment totals for charting.
 * @returns {{ key: string, label: string, amount: number, isFuture: boolean, isCurrent: boolean, payments?: object[] }[]}
 */
export function buildPaymentFlowSeries(scheduleItems = [], {
  monthsBefore = 5,
  monthsAfter = 6,
  referenceDate = new Date(),
} = {}) {
  const todayKey = monthKeyFromDate(referenceDate);
  const startKey = addMonthsToKey(todayKey, -monthsBefore);
  const endKey = addMonthsToKey(todayKey, monthsAfter);

  const buckets = {};
  for (const item of scheduleItems || []) {
    const key = monthKeyFromDate(item.date);
    if (!key || key < startKey || key > endKey) continue;
    if (!buckets[key]) buckets[key] = { total: 0, items: [] };
    buckets[key].total += Number(item.amount || 0);
    buckets[key].items.push(item);
  }

  const points = [];
  let cursor = startKey;
  while (cursor <= endKey) {
    const bucket = buckets[cursor];
    points.push({
      key: cursor,
      label: formatMonthLabel(cursor),
      amount: bucket?.total || 0,
      isFuture: cursor > todayKey,
      isCurrent: cursor === todayKey,
      payments: aggregatePayments(bucket?.items),
    });
    cursor = addMonthsToKey(cursor, 1);
  }
  return points;
}

/** Daily payment totals within a single month. */
export function buildPaymentFlowDailySeries(scheduleItems = [], monthKey, referenceDate = new Date()) {
  const [year, month] = monthKey.split('-').map(Number);
  const lastDay = daysInMonth(year, month);
  const todayStr = todayDateStr(referenceDate);
  const buckets = {};

  for (const item of scheduleItems || []) {
    if (monthKeyFromDate(item.date) !== monthKey) continue;
    const dateStr = item.date.slice(0, 10);
    if (!buckets[dateStr]) buckets[dateStr] = { total: 0, items: [] };
    buckets[dateStr].total += Number(item.amount || 0);
    buckets[dateStr].items.push(item);
  }

  const points = [];
  for (let day = 1; day <= lastDay; day += 1) {
    const dateStr = toDateStr(year, month, day);
    const bucket = buckets[dateStr];
    points.push({
      key: dateStr,
      label: formatDayLabel(dateStr),
      amount: bucket?.total || 0,
      isFuture: dateStr > todayStr,
      isCurrent: dateStr === todayStr,
      payments: aggregatePayments(bucket?.items),
    });
  }
  return points;
}

/** Weekly payment totals within a single month. */
export function buildPaymentFlowWeeklySeries(scheduleItems = [], monthKey, referenceDate = new Date()) {
  const [year, month] = monthKey.split('-').map(Number);
  const lastDay = daysInMonth(year, month);
  const todayStr = todayDateStr(referenceDate);
  const weeks = [];
  for (let start = 1; start <= lastDay; start += 7) {
    weeks.push({ start, end: Math.min(start + 6, lastDay) });
  }

  return weeks.map(({ start, end }) => {
    const startStr = toDateStr(year, month, start);
    const endStr = toDateStr(year, month, end);
    const matched = (scheduleItems || []).filter((item) => {
      const dateStr = item.date?.slice(0, 10);
      return dateStr >= startStr && dateStr <= endStr;
    });
    const amount = matched.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    return {
      key: `${monthKey}-w${start}`,
      label: formatWeekLabel(start, end),
      amount,
      isFuture: startStr > todayStr,
      isCurrent: todayStr >= startStr && todayStr <= endStr,
      payments: aggregatePayments(matched),
    };
  });
}

export function buildChartYScale(values = [], budget = null, monthlyEstimate = 0, { includeGuides = true } = {}) {
  const numericBudget = includeGuides ? Number(budget || 0) : 0;
  const numericEstimate = includeGuides ? Number(monthlyEstimate || 0) : 0;
  const dataPeak = Math.max(...values, 1);
  const peak = Math.max(dataPeak, numericBudget, numericEstimate);
  const padded = Math.ceil(peak * 1.1);
  const step = padded <= 50000 ? 5000 : padded <= 150000 ? 10000 : 25000;
  const maxY = Math.max(Math.ceil(padded / step) * step, numericBudget, numericEstimate, step);

  const ticks = [0];
  for (let v = step; v < maxY; v += step) ticks.push(v);
  if (!ticks.includes(maxY)) ticks.push(maxY);

  return { maxY, ticks };
}

/** Stats for a focused month in day/week chart footers. */
export function buildFocusMonthStats(scheduleItems = [], monthKey, referenceDate = new Date()) {
  const todayStr = todayDateStr(referenceDate);
  const matched = (scheduleItems || []).filter(
    (item) => monthKeyFromDate(item.date) === monthKey,
  );

  let paidTotal = 0;
  let scheduledTotal = 0;
  matched.forEach((item) => {
    const amount = Number(item.amount || 0);
    const dateStr = item.date?.slice(0, 10) || '';
    if (dateStr && dateStr <= todayStr) paidTotal += amount;
    else scheduledTotal += amount;
  });

  return {
    paymentCount: matched.length,
    paidTotal,
    scheduledTotal,
    total: paidTotal + scheduledTotal,
  };
}

/** notes 필드에서 affiliate_ 프로모션 문구 추출 */
export function parsePromoNotes(notes) {
  if (!notes) return [];
  return notes
    .split('|')
    .map((part) => part.trim())
    .filter((part) => part.startsWith('affiliate_'))
    .map((part) => {
      const body = part.replace(/^affiliate_/, '');
      const eq = body.indexOf('=');
      if (eq === -1) return body;
      return `${body.slice(0, eq)} ${Number(body.slice(eq + 1)).toLocaleString('ko-KR')}원`;
    });
}

export function buildCalcItemFromPlan(plan, itemType = 'plan') {
  return {
    uid: `${itemType}-${plan.id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    item_type: itemType,
    plan_id: plan.id,
    platform_id: plan.platform,
    platform_name: plan.platform_name,
    plan_name: plan.plan_name,
    price: plan.price,
    billing_period: plan.billing_period,
    monthly_price: planMonthlyPrice(plan),
    notes: plan.notes,
    bundle_contents: plan.bundle_contents || [],
  };
}

export function buildCalcItemFromAddon(passItem, pricing, platformName) {
  return {
    uid: `addon-${pricing.id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    item_type: 'addon',
    plan_id: null,
    addon_pricing_id: pricing.id,
    platform_id: passItem.platform,
    platform_name: platformName,
    plan_name: pricing.base_plan_name
      ? `${passItem.pass_name} · ${pricing.base_plan_name}`
      : passItem.pass_name,
    price: pricing.price,
    billing_period: pricing.billing_period,
    monthly_price: planMonthlyPrice(pricing),
    notes: '',
    bundle_contents: [],
  };
}

export function itemTypeLabel(itemType) {
  if (itemType === 'bundle') return '번들';
  if (itemType === 'addon') return '애드온';
  if (itemType === 'related_bundle') return '제휴 번들';
  return '요금제';
}

export function isBundleCalcItem(item) {
  return item?.item_type === 'bundle' || item?.item_type === 'related_bundle';
}

function sameCalcPlatform(a, b) {
  return a != null && b != null && String(a) === String(b);
}

/** @returns {{ allowed: boolean, message: string }} */
export function canAddCalcItem(item, existingItems = []) {
  if (!item) {
    return { allowed: false, message: '' };
  }

  const items = existingItems || [];

  if (item.plan_id != null && items.some((existing) => existing.plan_id === item.plan_id)) {
    return { allowed: false, message: '이미 계산기에 추가된 요금제입니다.' };
  }

  if (
    item.addon_pricing_id != null
    && items.some((existing) => existing.addon_pricing_id === item.addon_pricing_id)
  ) {
    return { allowed: false, message: '이미 계산기에 추가된 패스입니다.' };
  }

  if (isBundleCalcItem(item)) {
    return { allowed: true, message: '' };
  }

  const platformId = item.platform_id;
  if (platformId == null) {
    return { allowed: true, message: '' };
  }

  const platformName = item.platform_name || '해당 플랫폼';

  if (items.some((existing) => sameCalcPlatform(existing.platform_id, platformId) && !isBundleCalcItem(existing))) {
    return {
      allowed: false,
      message: `${platformName}은(는) 이미 다른 요금제로 계산기에 포함되어 있습니다.`,
    };
  }

  if (items.some((existing) => sameCalcPlatform(existing.platform_id, platformId) && isBundleCalcItem(existing))) {
    return {
      allowed: false,
      message: `${platformName}은(는) 번들 상품으로 이미 계산기에 포함되어 있습니다.`,
    };
  }

  return { allowed: true, message: '' };
}
