<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const open = ref(false);
const loading = ref(false);
const notifications = ref([]);
const readIds = ref(new Set(JSON.parse(localStorage.getItem('ws-notif-read') || '[]')));
const bellRef = ref(null);
const panelStyle = ref({});

const unreadCount = computed(() =>
  notifications.value.filter((n) => !readIds.value.has(n.id)).length,
);

function updatePanelPosition() {
  const el = bellRef.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  panelStyle.value = {
    top: `${rect.bottom + 8}px`,
    right: `${Math.max(12, window.innerWidth - rect.right)}px`,
  };
}

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
  if (open.value) {
    updatePanelPosition();
    loadNotifications();
  }
}

function closePanel() {
  open.value = false;
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
  if (!event.target.closest('.notif-wrap') && !event.target.closest('.notif-panel')) {
    closePanel();
  }
}

function onViewportChange() {
  if (open.value) updatePanelPosition();
}

function typeIcon(type) {
  if (type === 'budget') return '₩';
  return '↻';
}

watch(() => session.isAuthenticated, loadNotifications);
onMounted(() => {
  loadNotifications();
  document.addEventListener('click', onClickOutside);
  window.addEventListener('resize', onViewportChange);
  window.addEventListener('scroll', onViewportChange, { passive: true });
});

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside);
  window.removeEventListener('resize', onViewportChange);
  window.removeEventListener('scroll', onViewportChange);
});

defineExpose({ loadNotifications, notifications });
</script>

<template>
  <div v-if="session.isAuthenticated" class="notif-wrap">
    <button
      ref="bellRef"
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

    <Teleport to="body">
      <div v-if="open" class="notif-panel" :style="panelStyle" @click.stop>
        <div class="panel-head">
          <strong>알림</strong>
          <div class="panel-actions">
            <button v-if="unreadCount" type="button" class="mark-all" @click="markAllRead">모두 읽음</button>
            <button type="button" class="panel-close" aria-label="알림 닫기" @click="closePanel">×</button>
          </div>
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
    </Teleport>
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
  border: 1px solid var(--ws-glass-border);
  border-radius: var(--ws-radius-sm);
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  color: var(--ws-text);
  box-shadow: var(--ws-glass-highlight);
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
  position: fixed;
  z-index: 5000;
  width: min(360px, calc(100vw - 24px));
  max-height: min(420px, calc(100vh - 96px));
  overflow: auto;
  border: 1px solid var(--ws-glass-border-strong);
  border-radius: var(--ws-radius);
  background: rgba(12, 18, 32, 0.92);
  box-shadow: var(--ws-glass-shadow-lg), var(--ws-glass-highlight);
  backdrop-filter: blur(var(--ws-glass-blur-heavy)) saturate(var(--ws-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ws-glass-blur-heavy)) saturate(var(--ws-glass-saturate));
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--ws-border);
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mark-all {
  border: none;
  background: none;
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.panel-close {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  cursor: pointer;
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
}

.panel-close:hover {
  border-color: var(--ws-primary);
  color: var(--ws-primary);
}

.notif-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.notif-list li.unread {
  background: rgba(var(--ws-primary-rgb), 0.08);
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
