<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import SubscriptionCalendar from './SubscriptionCalendar.vue';
import PaymentFlowChart from './PaymentFlowChart.vue';
import { backendRoutes, backendUrl } from '../config/backend';
import { profileInitial } from '../utils/formatters';
import { useSessionStore } from '../stores/session';
import { subscriptionMonthlyAmount, subscriptionsMonthlyTotal } from '../utils/billing';

const session = useSessionStore();

const dashboard = ref(null);
const error = ref('');
const selectedCalendarSubId = ref(null);

const standaloneSubs = computed(() => dashboard.value?.standalone_subscriptions || []);
const bundleSubs = computed(() => dashboard.value?.bundle_subscriptions || []);
const allSubscriptions = computed(() => dashboard.value?.subscriptions || []);
const profileName = computed(() => session.user?.nickname || session.user?.username || '?');
const profileAvatarInitial = computed(() => profileInitial(profileName.value));
const monthlyTotal = computed(() => {
  if (allSubscriptions.value.length) return subscriptionsMonthlyTotal(allSubscriptions.value);
  return dashboard.value?.monthly_total || 0;
});
const monthlyBudget = computed(() => {
  const cap = dashboard.value?.monthly_spend_cap;
  return cap != null && cap !== '' ? Number(cap) : null;
});

function money(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function selectCalendarSub(subId) {
  selectedCalendarSubId.value = subId;
}

async function load() {
  dashboard.value = await apiRequest('/api/accounts/dashboard/');
}

async function removeSubscription(id) {
  if (!confirm('이 구독을 삭제할까요?')) return;
  await apiRequest(`/api/accounts/subscriptions/${id}/delete/`, { method: 'DELETE' });
  if (selectedCalendarSubId.value === id) {
    selectedCalendarSubId.value = null;
  }
  await load();
}

onMounted(async () => {
  try {
    await load();
  } catch (err) {
    error.value = err.message;
  }
});
</script>

<template>
  <section class="subscription-dashboard">
    <header class="subscription-section-head">
      <div>
        <p class="eyebrow">Subscription</p>
        <h2>구독 관리</h2>
      </div>
      <div class="dashboard-actions">
        <RouterLink class="button primary" to="/subscriptions/new">구독 추가</RouterLink>
        <RouterLink class="button" to="/subscriptions/receipt-scan">결제내역·이미지 스캔</RouterLink>
        <a class="button" :href="backendUrl(backendRoutes.onboardingGmail)">Gmail에서 찾기</a>
      </div>
    </header>

    <p v-if="error" class="notice">{{ error }}</p>
    <div v-else-if="!dashboard" class="loader">구독 정보를 불러오는 중입니다.</div>

    <template v-else>
      <div class="account panel">
        <div class="avatar">
          <img v-if="session.user?.profile_image" :src="session.user.profile_image" alt="" />
          <span v-else class="avatar-initial-letter" aria-hidden="true">{{ profileAvatarInitial }}</span>
        </div>
        <div class="account-copy">
          <strong>{{ session.user?.nickname || session.user?.username }}</strong>
          <span>{{ session.user?.email || '이메일 정보 없음' }}</span>
          <div
            v-if="dashboard.taste_titles?.habit || dashboard.taste_titles?.genre"
            class="taste-title-row"
          >
            <span v-if="dashboard.taste_titles?.habit" class="taste-title habit">{{ dashboard.taste_titles.habit }}</span>
            <span v-if="dashboard.taste_titles?.genre" class="taste-title genre">{{ dashboard.taste_titles.genre }}</span>
          </div>
          <p v-if="dashboard.taste_summary" class="taste-summary">{{ dashboard.taste_summary }}</p>
        </div>
      </div>

      <section class="grid-3">
        <article class="metric"><span>활성 구독</span><strong>{{ dashboard.subscription_count }}</strong></article>
        <article class="metric"><span>구독 플랫폼</span><strong>{{ dashboard.platform_count }}</strong></article>
        <article class="metric"><span>월 예상 지출</span><strong>{{ money(monthlyTotal) }}원</strong></article>
      </section>

      <section class="panel payment-flow-panel">
        <div class="payment-flow-head">
          <div>
            <h2>결제 흐름</h2>
            <p class="muted small">월·주·일 단위로 결제 시점을 확인하고 예산·월 예상 지출과 비교하세요.</p>
          </div>
          <div v-if="monthlyBudget != null && monthlyBudget > 0" class="budget-chip">
            예산 {{ money(monthlyBudget) }}원
          </div>
        </div>
        <PaymentFlowChart
          :schedule-items="dashboard.schedule_items || []"
          :budget="monthlyBudget"
          :monthly-estimate="monthlyTotal"
        />
      </section>

      <section class="panel calendar-panel">
        <h2>결제 캘린더</h2>
        <p class="muted small">결제일·만료일과 구독 기간을 확인하세요.</p>
        <SubscriptionCalendar
          :schedule-items="dashboard.schedule_items || []"
          :subscriptions="dashboard.calendar_events || []"
          :highlight-subscription-id="selectedCalendarSubId"
          @select-subscription="selectCalendarSub"
        />
      </section>

      <section class="grid-2 dashboard-grid">
        <div class="panel">
          <h2>구독 중인 플랫폼</h2>

          <div v-if="standaloneSubs.length" class="subscription-list">
            <RouterLink
              v-for="sub in standaloneSubs"
              :key="sub.id"
              class="subscription-row"
              :to="`/benchmark/platforms/${sub.platform}`"
            >
              <img v-if="sub.icon_url" class="sub-logo" :src="sub.icon_url" :alt="sub.platform_name" />
              <div v-else class="sub-logo fallback">{{ sub.platform_name.charAt(0) }}</div>
              <div class="sub-main">
                <strong>{{ sub.platform_name }}</strong>
                <span>{{ sub.plan_name }}</span>
                <span v-if="sub.period_start && sub.period_end" class="period">
                  구독 {{ sub.period_start }} ~ {{ sub.period_end }}
                </span>
              </div>
              <div class="price">
                {{ money(sub.payment_amount) }}원
                <small>{{ sub.billing_cycle_label }}</small>
                <small v-if="sub.billing_cycle !== 'monthly'">월 {{ money(subscriptionMonthlyAmount(sub)) }}원 환산</small>
              </div>
              <button class="delete-button" type="button" @click.prevent.stop="removeSubscription(sub.id)">
                삭제
              </button>
            </RouterLink>
          </div>

          <section v-if="bundleSubs.length" class="bundle-section">
            <h3>번들</h3>
            <article v-for="bundle in bundleSubs" :key="bundle.id" class="bundle-card">
              <div class="bundle-head">
                <div class="sub-main">
                  <strong>{{ bundle.plan_name }}</strong>
                  <span>{{ bundle.platform_name }}</span>
                  <span v-if="bundle.period_start && bundle.period_end" class="period">
                    {{ bundle.period_start }} ~ {{ bundle.period_end }}
                  </span>
                </div>
                <div class="price">
                  {{ money(bundle.payment_amount) }}원
                  <small>{{ bundle.billing_cycle_label }}</small>
                  <small v-if="bundle.billing_cycle !== 'monthly'">월 {{ money(subscriptionMonthlyAmount(bundle)) }}원 환산</small>
                </div>
                <button class="delete-button" type="button" @click.stop="removeSubscription(bundle.id)">
                  삭제
                </button>
              </div>
              <ul v-if="bundle.included_platforms?.length" class="bundle-platforms">
                <li v-for="p in bundle.included_platforms" :key="`${bundle.id}-${p.platform_id}`">
                  <RouterLink :to="`/benchmark/platforms/${p.platform_id}`">
                    <img v-if="p.icon_url" class="sub-logo sm" :src="p.icon_url" :alt="p.platform_name" />
                    <span v-else class="sub-logo sm fallback">{{ p.platform_name.charAt(0) }}</span>
                    <span>{{ p.platform_name }}</span>
                  </RouterLink>
                </li>
              </ul>
              <p v-else class="muted small">포함 플랫폼 정보가 없습니다.</p>
            </article>
          </section>

          <div v-if="!standaloneSubs.length && !bundleSubs.length" class="empty">
            아직 등록된 구독이 없습니다.
            <RouterLink class="button primary" to="/subscriptions/new">첫 구독 추가</RouterLink>
          </div>
        </div>

        <aside class="panel">
          <h2>결제 일정</h2>
          <div v-if="dashboard.timeline.length" class="timeline">
            <div v-for="item in dashboard.timeline" :key="`${item.name}-${item.date}`" class="timeline-row">
              <strong>{{ item.name }}</strong>
              <span>{{ item.days >= 0 ? `D-${item.days}` : `D+${Math.abs(item.days)}` }}</span>
            </div>
          </div>
          <div v-else class="empty">예정된 결제가 없습니다.</div>
        </aside>
      </section>
    </template>
  </section>
</template>

<style scoped>
.subscription-dashboard {
  display: grid;
  gap: 24px;
}

.subscription-section-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  padding-top: 4px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(var(--ws-secondary-rgb), 0.28);
}

.subscription-section-head h2 {
  margin: 2px 0 0;
  font-size: 24px;
}

.dashboard-actions {
  display: flex;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 10px;
}

.account {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.account-copy {
  min-width: 0;
}

.account-copy strong {
  display: block;
}

.taste-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.taste-title {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}

.taste-title.habit {
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.35);
  background: rgba(var(--ws-secondary-rgb), 0.12);
  color: var(--ws-secondary);
}

.taste-title.genre {
  border: 1px solid rgba(var(--ws-primary-rgb), 0.35);
  background: rgba(var(--ws-primary-rgb), 0.12);
  color: var(--ws-primary);
}

.taste-summary {
  margin: 8px 0 0;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  flex: none;
  border: none;
  box-shadow: none;
  background: var(--ws-surface-2);
}

.avatar .avatar-initial-letter {
  font-size: 24px;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border: none;
}

.account span,
.sub-main span,
.price small {
  display: block;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
}

.payment-flow-panel h2 {
  margin: 0 0 4px;
}

.payment-flow-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.budget-chip {
  flex: none;
  padding: 8px 12px;
  border: 1px solid rgba(255, 77, 77, 0.4);
  border-radius: 999px;
  background: rgba(255, 77, 77, 0.1);
  color: #ffb4b4;
  font-size: 13px;
  font-weight: 900;
}

.calendar-panel {
  background: #0b1220;
}

.calendar-panel h2,
.calendar-panel .muted {
  color: #e2e8f0;
}

.calendar-panel h2 {
  margin: 0 0 4px;
}

.calendar-panel .muted {
  margin-bottom: 14px;
}

.dashboard-grid .panel > h2 {
  margin: 0 0 14px;
}

.dashboard-grid,
.subscription-list,
.timeline,
.bundle-platforms {
  display: grid;
  gap: 10px;
}

.subscription-list {
  gap: 12px;
}

.timeline {
  gap: 0;
  margin-top: 2px;
}

.dashboard-grid {
  margin-top: 4px;
}

.bundle-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--ws-border);
}

.bundle-section h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.bundle-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.bundle-head .sub-main {
  gap: 7px;
}

.bundle-card {
  padding: 14px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.bundle-platforms {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}

.bundle-platforms li a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  color: inherit;
  text-decoration: none;
  font-weight: 700;
  font-size: 14px;
}

.bundle-platforms li a:hover {
  border-color: var(--ws-secondary);
}

.subscription-row {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
  padding: 14px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
}

.sub-main {
  display: grid;
  gap: 6px;
}

.sub-main strong {
  line-height: 1.35;
}

.sub-main span {
  line-height: 1.45;
}

.subscription-row:hover {
  border-color: var(--ws-secondary);
  background: var(--ws-surface-2);
}

.sub-main .period {
  color: var(--ws-text);
  font-weight: 600;
}

.sub-logo {
  width: 46px;
  height: 46px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  object-fit: contain;
  background: var(--ws-surface-2);
}

.sub-logo.sm {
  width: 32px;
  height: 32px;
}

.sub-logo.fallback {
  display: grid;
  place-items: center;
  background: var(--ws-surface-2);
  color: var(--ws-secondary);
  font-weight: 800;
}

.price {
  text-align: right;
  font-weight: 900;
}

.delete-button {
  min-height: 36px;
  border: 1px solid rgba(255, 77, 77, 0.35);
  border-radius: 8px;
  background: rgba(255, 77, 77, 0.08);
  color: #ffb4b4;
  cursor: pointer;
  font-weight: 800;
}

.timeline-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--ws-border);
}

.timeline-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.timeline-row:first-child {
  padding-top: 0;
}

@media (max-width: 620px) {
  .dashboard-actions {
    justify-content: stretch;
  }

  .dashboard-actions .button {
    flex: 1;
  }

  .subscription-row,
  .bundle-head {
    grid-template-columns: 46px minmax(0, 1fr);
  }

  .price,
  .delete-button {
    grid-column: 2;
    justify-self: start;
    text-align: left;
  }
}
</style>
