<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { createCommunityPost, fetchCommunityBoards } from '../api/community';
import { fetchSubscriptionPlatforms } from '../api/subscriptions';
import { useSessionStore } from '../stores/session';
import PageHeader from '../components/PageHeader.vue';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const boards = ref([]);
const platforms = ref([]);
const error = ref('');
const submitting = ref(false);
const form = ref({
  board: typeof route.query.board === 'string' ? route.query.board : 'ott',
  platform_id: route.query.platform_id ? Number(route.query.platform_id) : null,
  title: '',
  content: '',
});

const isAdmin = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const activeBoard = computed(() => boards.value.find((board) => board.key === form.value.board));
const selectedPlatform = computed(() =>
  platforms.value.find((item) => Number(item.id) === Number(form.value.platform_id)) || null,
);
const showPlatformPicker = computed(() => form.value.board === 'ott');

function normalizeBoardSelection() {
  const requestedBoard = boards.value.find((board) => board.key === form.value.board);
  if (!requestedBoard || (requestedBoard.key === 'notice' && !isAdmin.value)) {
    form.value.board = 'ott';
  }
  if (form.value.board !== 'ott') {
    form.value.platform_id = null;
  }
}

async function loadBoards() {
  boards.value = await fetchCommunityBoards();
  normalizeBoardSelection();
}

async function loadPlatforms() {
  try {
    platforms.value = await fetchSubscriptionPlatforms();
  } catch {
    platforms.value = [];
  }
}

async function submit() {
  error.value = '';
  if (!session.isAuthenticated) {
    alert('로그인 후 글을 작성할 수 있습니다.');
    router.push('/login');
    return;
  }

  normalizeBoardSelection();
  if (form.value.board === 'ott' && !form.value.platform_id) {
    error.value = 'OTT 게시판에서는 플랫폼(플레어)을 선택해주세요.';
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      board: form.value.board,
      title: form.value.title,
      content: form.value.content,
    };
    if (form.value.board === 'ott') {
      payload.platform_id = form.value.platform_id;
    }
    const post = await createCommunityPost(payload);
    router.push(`/community/${post.id}`);
  } catch (err) {
    error.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  if (!session.isAuthenticated) {
    alert('로그인 후 글을 작성할 수 있습니다.');
    router.push('/login');
    return;
  }
  await Promise.all([loadBoards(), loadPlatforms()]);
});
</script>

<template>
  <main>
    <PageHeader
      eyebrow="Community"
      title="새 글 작성"
      :description="activeBoard ? `${activeBoard.name}에 글을 작성합니다.` : '커뮤니티에 글을 작성합니다.'"
    >
      <template #actions>
        <RouterLink class="button" to="/community">목록</RouterLink>
      </template>
    </PageHeader>

    <section class="panel write-page">
      <p v-if="error" class="notice">{{ error }}</p>
      <form class="write-form" @submit.prevent="submit">
        <div class="board-chip">
          <span>게시판</span>
          <strong>{{ activeBoard?.name || '게시판' }}</strong>
        </div>

        <div v-if="showPlatformPicker" class="field">
          <label for="platform">플랫폼 플레어</label>
          <select id="platform" v-model.number="form.platform_id" required>
            <option :value="null" disabled>플랫폼 선택</option>
            <option v-for="platform in platforms" :key="platform.id" :value="platform.id">
              {{ platform.name }}
            </option>
          </select>
          <p v-if="selectedPlatform" class="muted">글에 <span class="flair">{{ selectedPlatform.name }}</span> 플레어가 표시됩니다.</p>
        </div>

        <div class="field">
          <label for="title">제목</label>
          <input id="title" v-model="form.title" maxlength="120" required />
        </div>
        <div class="field">
          <label for="content">내용</label>
          <textarea id="content" v-model="form.content" rows="12" required></textarea>
        </div>
        <div class="write-actions">
          <RouterLink class="button" to="/community">취소</RouterLink>
          <button class="button primary" type="submit" :disabled="submitting">등록</button>
        </div>
      </form>
    </section>
  </main>
</template>

<style scoped>
.write-page {
  max-width: 860px;
}

.write-form {
  display: grid;
  gap: 14px;
}

.board-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
}

.board-chip span {
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 900;
}

.board-chip strong {
  color: var(--ws-text);
}

.field {
  display: grid;
  gap: 7px;
}

.field label {
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 900;
}

.field input,
.field textarea,
.field select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
}

.field textarea {
  resize: vertical;
}

.flair {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: rgba(217, 221, 146, 0.2);
  color: var(--ws-primary);
}

.write-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
