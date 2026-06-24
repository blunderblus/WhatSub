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
