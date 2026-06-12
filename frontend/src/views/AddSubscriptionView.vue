<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { apiRequest } from '../api/http';

const router = useRouter();
const platforms = ref([]);
const plans = ref([]);
const error = ref('');
const today = new Date().toISOString().slice(0, 10);
const form = ref({
  platform: '',
  plan: '',
  plan_name: '',
  payment_amount: '',
  billing_cycle: 'monthly',
  payment_method: '',
  start_date: today,
  renewal_date: today,
  auto_renew: true,
  memo: '',
});

const filteredPlans = computed(() => plans.value.filter((plan) => String(plan.platform) === String(form.value.platform)));

watch(() => form.value.plan, (planId) => {
  const plan = plans.value.find((item) => String(item.id) === String(planId));
  if (!plan) return;
  form.value.plan_name = plan.plan_name;
  form.value.payment_amount = plan.price;
  form.value.billing_cycle = plan.billing_period;
});

async function submit() {
  error.value = '';
  try {
    await apiRequest('/api/accounts/subscriptions/', { method: 'POST', body: form.value });
    router.push('/subscriptions');
  } catch (err) {
    error.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
  }
}

onMounted(async () => {
  const [platformData, planData] = await Promise.all([
    apiRequest('/api/subscriptions/platforms/'),
    apiRequest('/api/subscriptions/plans/'),
  ]);
  platforms.value = platformData;
  plans.value = planData;
});
</script>

<template>
  <main class="form-card">
    <p class="eyebrow">Add subscription</p>
    <h1>구독 직접 추가</h1>
    <p class="muted">플랫폼과 요금제를 고르면 금액과 결제 주기가 자동으로 채워집니다.</p>
    <p v-if="error" class="notice">{{ error }}</p>
    <form @submit.prevent="submit">
      <div class="field">
        <label for="platform">플랫폼</label>
        <select id="platform" v-model="form.platform" required>
          <option value="">플랫폼 선택</option>
          <option v-for="platform in platforms" :key="platform.id" :value="platform.id">{{ platform.name }}</option>
        </select>
      </div>
      <div class="field">
        <label for="plan">요금제</label>
        <select id="plan" v-model="form.plan">
          <option value="">직접 입력</option>
          <option v-for="plan in filteredPlans" :key="plan.id" :value="plan.id">
            {{ plan.plan_name }} · {{ Number(plan.price).toLocaleString('ko-KR') }}원
          </option>
        </select>
      </div>
      <div class="form-row">
        <div class="field"><label for="plan_name">요금제 이름</label><input id="plan_name" v-model="form.plan_name" /></div>
        <div class="field"><label for="payment_amount">결제 금액</label><input id="payment_amount" v-model="form.payment_amount" type="number" min="0" required /></div>
      </div>
      <div class="form-row">
        <div class="field">
          <label for="billing_cycle">결제 주기</label>
          <select id="billing_cycle" v-model="form.billing_cycle">
            <option value="weekly">주간</option>
            <option value="monthly">월간</option>
            <option value="annual">연간</option>
          </select>
        </div>
        <div class="field"><label for="payment_method">결제 수단</label><input id="payment_method" v-model="form.payment_method" /></div>
      </div>
      <div class="form-row">
        <div class="field"><label for="start_date">시작일</label><input id="start_date" v-model="form.start_date" type="date" required /></div>
        <div class="field"><label for="renewal_date">갱신일</label><input id="renewal_date" v-model="form.renewal_date" type="date" required /></div>
      </div>
      <div class="field"><label for="memo">메모</label><textarea id="memo" v-model="form.memo"></textarea></div>
      <label class="checkbox"><input v-model="form.auto_renew" type="checkbox" /> 자동 갱신</label>
      <button class="button primary full-width" style="margin-top: 22px" type="submit">구독 추가</button>
    </form>
  </main>
</template>

<style scoped>
.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  color: #44515e;
  font-weight: 800;
}
</style>
