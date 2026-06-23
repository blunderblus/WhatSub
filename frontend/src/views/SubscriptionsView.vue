<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import PageHeader from '../components/PageHeader.vue';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();

const dashboard = ref(null);
const error = ref('');

function money(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

async function load() {
  dashboard.value = await apiRequest('/api/accounts/dashboard/');
}

async function removeSubscription(id) {
  if (!confirm('이 구독을 삭제할까요?')) return;
  await apiRequest(`/api/accounts/subscriptions/${id}/delete/`, { method: 'DELETE' });
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
  <main>
    <PageHeader eyebrow="My Subscriptions" title="내 구독 대시보드">
      <template #actions>
        <div class="actions">
          <RouterLink class="button primary" to="/subscriptions/new">구독 추가</RouterLink>
          <a class="button" href="http://127.0.0.1:8000/accounts/onboarding/gmail/">Gmail에서 찾기</a>
        </div>
      </template>
    </PageHeader>

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
        <article class="metric"><span>월 예상 지출</span><strong>{{ money(dashboard.monthly_total) }}원</strong></article>
      </section>

      <section class="grid-2" style="margin-top: 18px">
        <div class="panel">
          <h2>구독 중인 플랫폼</h2>
          <div v-if="dashboard.subscriptions.length" class="subscription-list">
            <article v-for="sub in dashboard.subscriptions" :key="sub.id" class="subscription-row">
              <img v-if="sub.icon_url" class="sub-logo" :src="sub.icon_url" :alt="sub.platform_name" />
              <div v-else class="sub-logo fallback">{{ sub.platform_name.charAt(0) }}</div>
              <div class="sub-main">
                <strong>{{ sub.platform_name }}</strong>
                <span>{{ sub.plan_name }} · 갱신 {{ sub.renewal_date }}</span>
              </div>
              <div class="price">
                {{ money(sub.payment_amount) }}원
                <small>{{ sub.billing_cycle_label }}</small>
              </div>
              <button class="delete-button" type="button" @click="removeSubscription(sub.id)">삭제</button>
            </article>
          </div>
          <div v-else class="empty">
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
  </main>
</template>

<style scoped>
.account {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: var(--ws-primary);
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

.subscription-list,
.timeline {
  display: grid;
  gap: 10px;
  margin-top: 14px;
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
}

.sub-logo {
  width: 46px;
  height: 46px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  object-fit: contain;
  background: var(--ws-surface-2);
}

.sub-logo.fallback {
  display: grid;
  place-items: center;
  background: var(--ws-surface-2);
  color: var(--ws-primary);
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
  .subscription-row {
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
