<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const open = ref(false);
const loading = ref(false);
const notifications = ref([]);
const readIds = ref(new Set(JSON.parse(localStorage.getItem('ws-notif-read') || '[]')));

const unreadCount = computed(() =>
  notifications.value.filter((n) => !readIds.value.has(n.id)).length,
);

async function loadNotifications() {
  if (!session.isAuthenticated) {
    notifications.value = [];
    return;
  }
  loading.value = true;
  try {
    const data = await apiRequest('/api/accounts/notifications/?days=14');
    notifications.value = data.notifications || [];
  } catch {
    notifications.value = [];
  } finally {
    loading.value = false;
  }
}

function togglePanel() {
  open.value = !open.value;
  if (open.value) loadNotifications();
}

function markRead(id) {
  readIds.value = new Set([...readIds.value, id]);
  localStorage.setItem('ws-notif-read', JSON.stringify([...readIds.value]));
}

function markAllRead() {
  readIds.value = new Set(notifications.value.map((n) => n.id));
  localStorage.setItem('ws-notif-read', JSON.stringify([...readIds.value]));
}

function onClickOutside(event) {
  if (!event.target.closest('.notif-wrap')) open.value = false;
}

function typeIcon(type) {
  if (type === 'budget') return '₩';
  return '↻';
}

watch(() => session.isAuthenticated, loadNotifications);
onMounted(() => {
  loadNotifications();
  document.addEventListener('click', onClickOutside);
});

defineExpose({ loadNotifications, notifications });
</script>

<template>
  <div v-if="session.isAuthenticated" class="notif-wrap">
    <button
      type="button"
      class="bell-btn"
      aria-label="알림"
      :aria-expanded="open"
      @click.stop="togglePanel"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      <span v-if="unreadCount" class="badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <div v-if="open" class="notif-panel" @click.stop>
      <div class="panel-head">
        <strong>알림</strong>
        <button v-if="unreadCount" type="button" class="mark-all" @click="markAllRead">모두 읽음</button>
      </div>
      <div v-if="loading" class="panel-empty">불러오는 중...</div>
      <ul v-else-if="notifications.length" class="notif-list">
        <li
          v-for="n in notifications"
          :key="n.id"
          :class="{ unread: !readIds.has(n.id), urgent: n.urgency === 'high' }"
        >
          <RouterLink :to="n.link" @click="markRead(n.id); open = false">
            <span class="icon">{{ typeIcon(n.type) }}</span>
            <div>
              <strong>{{ n.title }}</strong>
              <span>{{ n.body }}</span>
            </div>
          </RouterLink>
        </li>
      </ul>
      <p v-else class="panel-empty">새 알림이 없습니다.</p>
    </div>
  </div>
</template>

<style scoped>
.notif-wrap {
  position: relative;
}

.bell-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  cursor: pointer;
  color: var(--ws-text);
}

.bell-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  line-height: 16px;
  text-align: center;
}

.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 100;
  width: min(360px, 90vw);
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--ws-border);
  border-radius: 12px;
  background: var(--ws-surface);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--ws-border);
}

.mark-all {
  border: none;
  background: none;
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.notif-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.notif-list li.unread {
  background: #f8fafc;
}

.notif-list li.urgent a strong {
  color: #b45309;
}

.notif-list a {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid var(--ws-border);
}

.notif-list a:hover {
  background: var(--ws-surface-2);
}

.icon {
  flex: none;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--ws-surface-2);
  font-size: 14px;
  font-weight: 800;
}

.notif-list strong {
  display: block;
  font-size: 13px;
  margin-bottom: 2px;
}

.notif-list span {
  display: block;
  font-size: 12px;
  color: var(--ws-muted);
}

.panel-empty {
  padding: 24px 14px;
  text-align: center;
  color: var(--ws-muted);
  font-size: 13px;
}
</style>
