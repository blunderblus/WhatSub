<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';
import PageHeader from '../components/PageHeader.vue';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const boards = ref([]);
const error = ref('');
const submitting = ref(false);
const form = ref({
  board: typeof route.query.board === 'string' ? route.query.board : 'ott',
  title: '',
  content: '',
});

const isAdmin = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const activeBoard = computed(() => boards.value.find((board) => board.key === form.value.board));

function normalizeBoardSelection() {
  const requestedBoard = boards.value.find((board) => board.key === form.value.board);
  if (!requestedBoard || (requestedBoard.key === 'notice' && !isAdmin.value)) {
    form.value.board = 'ott';
  }
}

async function loadBoards() {
  const data = await apiRequest('/api/community/boards/');
  boards.value = data.boards || [];
  normalizeBoardSelection();
}

async function submit() {
  error.value = '';
  if (!session.isAuthenticated) {
    alert('로그인 후 글을 작성할 수 있습니다.');
    router.push('/login');
    return;
  }

  normalizeBoardSelection();
  submitting.value = true;
  try {
    const post = await apiRequest('/api/community/posts/', {
      method: 'POST',
      body: form.value,
    });
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
  await loadBoards();
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
.field textarea {
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

.write-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
