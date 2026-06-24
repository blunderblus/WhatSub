import { computed, ref, watch } from 'vue';
import { fetchSubscriptionPlatforms, fetchSubscriptionPlans } from '../api/subscriptions';

export function useSubscriptionPlanPicker() {
  const platforms = ref([]);
  const plans = ref([]);
  const selectedPlatformId = ref('');
  const selectedPlanId = ref('');
  const loading = ref(false);
  const error = ref('');

  const filteredPlans = computed(() => {
    if (!selectedPlatformId.value) return [];
    return plans.value.filter((plan) => String(plan.platform) === String(selectedPlatformId.value));
  });

  const selectedPlan = computed(() =>
    filteredPlans.value.find((plan) => String(plan.id) === String(selectedPlanId.value)) || null,
  );

  watch(selectedPlatformId, () => {
    selectedPlanId.value = '';
  });

  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const [platformData, planData] = await Promise.all([
        fetchSubscriptionPlatforms(),
        fetchSubscriptionPlans(),
      ]);
      platforms.value = platformData;
      plans.value = planData;
    } catch (err) {
      error.value = err.message;
      platforms.value = [];
      plans.value = [];
    } finally {
      loading.value = false;
    }
  }

  return {
    platforms,
    plans,
    filteredPlans,
    selectedPlatformId,
    selectedPlanId,
    selectedPlan,
    loading,
    error,
    load,
  };
}
