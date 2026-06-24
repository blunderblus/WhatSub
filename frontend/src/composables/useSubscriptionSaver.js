import { computed, ref } from 'vue';
import { createUserSubscription, fetchUserSubscriptionDashboard } from '../api/subscriptions';
import { formatDateInput, renewalDateFrom } from '../utils/subscriptionDates';

function subscriptionPayloadFromCalcItem(item) {
  const startDate = new Date();
  const billingCycle = item.billing_period || 'monthly';

  return {
    platform: item.platform_id,
    plan: item.plan_id || '',
    plan_name: item.plan_name,
    payment_amount: item.price,
    billing_cycle: billingCycle,
    payment_method: '',
    start_date: formatDateInput(startDate),
    renewal_date: formatDateInput(renewalDateFrom(startDate, billingCycle)),
    auto_renew: true,
    memo: '구독 계산기에서 추가',
  };
}

export function useSubscriptionSaver() {
  const savingIds = ref(new Set());
  const savedIds = ref(new Set());
  const existingPlatformIds = ref(new Set());
  const error = ref('');
  const success = ref('');
  const loadingExisting = ref(false);

  const isSaving = (uid) => savingIds.value.has(uid);
  const isSaved = (uid) => savedIds.value.has(uid);
  const isExisting = (item) => (
    item?.platform_id != null && existingPlatformIds.value.has(String(item.platform_id))
  );
  const isBusy = computed(() => savingIds.value.size > 0);

  async function loadExistingSubscriptions() {
    loadingExisting.value = true;
    try {
      const dashboard = await fetchUserSubscriptionDashboard();
      existingPlatformIds.value = new Set(
        (dashboard.subscriptions || []).map((subscription) => String(subscription.platform)),
      );
    } catch {
      existingPlatformIds.value = new Set();
    } finally {
      loadingExisting.value = false;
    }
  }

  function markAsSaved(item) {
    savedIds.value = new Set([...savedIds.value, item.uid]);
    existingPlatformIds.value = new Set([...existingPlatformIds.value, String(item.platform_id)]);
  }

  async function saveCalcItem(item) {
    error.value = '';
    success.value = '';

    if (!item?.platform_id || !item?.plan_id) {
      error.value = '일반 요금제와 번들 요금제만 내 구독에 추가할 수 있습니다.';
      return null;
    }

    if (isExisting(item)) {
      error.value = `${item.platform_name}은(는) 이미 내 구독 목록에 있습니다.`;
      return null;
    }

    savingIds.value = new Set([...savingIds.value, item.uid]);
    try {
      const subscription = await createUserSubscription(subscriptionPayloadFromCalcItem(item));
      markAsSaved(item);
      success.value = `${item.platform_name} · ${item.plan_name}을(를) 내 구독에 추가했습니다.`;
      return subscription;
    } catch (err) {
      error.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
      return null;
    } finally {
      const nextSavingIds = new Set(savingIds.value);
      nextSavingIds.delete(item.uid);
      savingIds.value = nextSavingIds;
    }
  }

  async function saveCalcItems(items) {
    error.value = '';
    success.value = '';

    const saveTargets = items.filter((item) => item?.platform_id && item?.plan_id && !isExisting(item));
    if (!saveTargets.length) {
      error.value = '추가할 수 있는 새 구독이 없습니다.';
      return [];
    }

    const saved = [];
    for (const item of saveTargets) {
      const result = await saveCalcItem(item);
      if (result) saved.push(result);
    }

    if (saved.length) {
      success.value = `${saved.length}개 요금제를 내 구독에 추가했습니다.`;
    }
    return saved;
  }

  return {
    error,
    success,
    loadingExisting,
    isBusy,
    isSaving,
    isSaved,
    isExisting,
    loadExistingSubscriptions,
    saveCalcItem,
    saveCalcItems,
  };
}
