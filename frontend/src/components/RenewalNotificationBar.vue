<script setup>
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const notifications = ref([]);
const dismissed = ref(false);

async function loadRenewals() {
  if (!session.isAuthenticated) {
    notifications.value = [];
    return;
  }
  try {
    const data = await apiRequest('/api/accounts/renewals/?days=14');
    notifications.value = data.notifications || [];
    dismissed.value = false;
  } catch {
    notifications.value = [];
  }
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

watch(() => session.isAuthenticated, loadRenewals);
onMounted(loadRenewals);
</script>

<template>
  <div v-if="session.isAuthenticated && notifications.length && !dismissed" class="renewal-bar">
    <div class="renewal-copy">
      <strong>재결제 예정</strong>
      <ul>
        <li v-for="n in notifications.slice(0, 3)" :key="n.id">
          {{ n.platform_name }} · {{ formatDate(n.renewal_date) }}
          <span v-if="n.days_until === 0">(오늘)</span>
          <span v-else>(D-{{ n.days_until }})</span>
        </li>
      </ul>
      <RouterLink to="/subscriptions">내 구독에서 확인</RouterLink>
    </div>
    <button type="button" class="dismiss" aria-label="알림 닫기" @click="dismissed = true">×</button>
  </div>
</template>

<style scoped>
.renewal-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #fde68a;
  border-radius: 12px;
  background: #fffbeb;
  color: #92400e;
}

.renewal-copy strong {
  display: block;
  margin-bottom: 6px;
}

.renewal-copy ul {
  margin: 0 0 8px;
  padding-left: 18px;
  font-size: 14px;
}

.renewal-copy a {
  font-size: 13px;
  font-weight: 700;
  color: inherit;
}

.dismiss {
  border: none;
  background: none;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: inherit;
}
</style>
