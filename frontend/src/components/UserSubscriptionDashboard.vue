<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import SubscriptionCalendar from './SubscriptionCalendar.vue';
import { backendRoutes, backendUrl } from '../config/backend';
import { useSessionStore } from '../stores/session';
import { subscriptionMonthlyAmount, subscriptionsMonthlyTotal } from '../utils/billing';

const session = useSessionStore();

const dashboard = ref(null);
const error = ref('');
const selectedCalendarSubId = ref(null);

const standaloneSubs = computed(() => dashboard.value?.standalone_subscriptions || []);
const bundleSubs = computed(() => dashboard.value?.bundle_subscriptions || []);
const allSubscriptions = computed(() => dashboard.value?.subscriptions || []);
const monthlyTotal = computed(() => {
  if (allSubscriptions.value.length) return subscriptionsMonthlyTotal(allSubscriptions.value);
  return dashboard.value?.monthly_total || 0;
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
        <a class="button" :href="backendUrl(backendRoutes.onboardingGmail)">Gmail에서 찾기</a>
      </div>
    </header>

    <p v-if="error" class="notice">{{ error }}</p>
    <div v-else-if="!dashboard" class="loader">구독 정보를 불러오는 중입니다.</div>

    <template v-else>
      <div class="account panel">
        <div class="avatar">{{ (session.user?.nickname || session.user?.username || '?').charAt(0).toUpperCase() }}</div>
        <div>
          <strong>{{ session.user?.nickname || session.user?.username }}</strong>
          <span>{{ session.user?.email || '이메일 정보 없음' }}</span>
        </div>
      </div>

      <section class="grid-3">
        <article class="metric"><span>활성 구독</span><strong>{{ dashboard.subscription_count }}</strong></article>
        <article class="metric"><span>구독 플랫폼</span><strong>{{ dashboard.platform_count }}</strong></article>
        <article class="metric"><span>월 예상 지출</span><strong>{{ money(monthlyTotal) }}원</strong></article>
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
  align-items: center;
  gap: 12px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--ws-primary), var(--ws-secondary));
  color: var(--ws-primary-fg);
  font-size: 20px;
  font-weight: 800;
}

.account span,
.sub-main span,
.price small {
  display: block;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
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

.dashboard-grid,
.subscription-list,
.timeline,
.bundle-platforms {
  display: grid;
  gap: 10px;
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

.bundle-card {
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.bundle-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
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
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
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
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ws-border);
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
