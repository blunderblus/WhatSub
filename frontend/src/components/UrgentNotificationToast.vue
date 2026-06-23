<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const urgent = ref([]);
const dismissed = ref(new Set(JSON.parse(sessionStorage.getItem('ws-urgent-dismissed') || '[]')));

const visible = computed(() =>
  urgent.value.filter((n) => !dismissed.value.has(n.id)),
);

async function loadUrgent() {
  if (!session.isAuthenticated) {
    urgent.value = [];
    return;
  }
  try {
    const data = await apiRequest('/api/accounts/notifications/?days=14');
    urgent.value = data.urgent || [];
  } catch {
    urgent.value = [];
  }
}

function dismiss(id) {
  dismissed.value = new Set([...dismissed.value, id]);
  sessionStorage.setItem('ws-urgent-dismissed', JSON.stringify([...dismissed.value]));
}

function dismissAll() {
  dismissed.value = new Set(urgent.value.map((n) => n.id));
  sessionStorage.setItem('ws-urgent-dismissed', JSON.stringify([...dismissed.value]));
}

watch(() => session.isAuthenticated, loadUrgent);
onMounted(loadUrgent);
</script>

<template>
  <div v-if="visible.length" class="toast-stack" aria-live="polite">
    <div class="toast-head">
      <strong>긴급 알림</strong>
      <button type="button" class="dismiss-all" @click="dismissAll">모두 닫기</button>
    </div>
    <article v-for="n in visible.slice(0, 3)" :key="n.id" class="toast-card">
      <div class="toast-body">
        <strong>{{ n.title }}</strong>
        <p>{{ n.body }}</p>
        <RouterLink :to="n.link" @click="dismiss(n.id)">확인하기</RouterLink>
      </div>
      <button type="button" class="close" aria-label="닫기" @click="dismiss(n.id)">×</button>
    </article>
  </div>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 200;
  width: min(340px, calc(100vw - 40px));
  display: grid;
  gap: 10px;
}

.toast-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
  font-size: 12px;
  color: var(--ws-muted);
}

.dismiss-all {
  border: none;
  background: none;
  color: var(--ws-muted);
  font-size: 12px;
  cursor: pointer;
}

.toast-card {
  display: flex;
  gap: 8px;
  padding: 14px 14px 14px 16px;
  border: 1px solid #fde68a;
  border-left: 4px solid #f59e0b;
  border-radius: 12px;
  background: #fffbeb;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  color: #78350f;
}

.toast-body strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.toast-body p {
  margin: 0 0 8px;
  font-size: 13px;
}

.toast-body a {
  font-size: 12px;
  font-weight: 800;
  color: inherit;
}

.close {
  flex: none;
  border: none;
  background: none;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: inherit;
}
</style>
