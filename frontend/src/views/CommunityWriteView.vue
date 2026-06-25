<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { createCommunityPost, fetchCommunityBoards } from '../api/community';
import { fetchBenchmarkLeaderboard } from '../api/benchmark';
import CommunityFlair from '../components/CommunityFlair.vue';
import PageHeader from '../components/PageHeader.vue';
import { FLAIR_OTHER } from '../utils/platformFlair';
import { useSessionStore } from '../stores/session';

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
  flair_tag: '',
  title: '',
  content: '',
});

const isAdmin = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const activeBoard = computed(() => boards.value.find((board) => board.key === form.value.board));
const showPlatformPicker = computed(() => form.value.board === 'ott');
const writableBoards = computed(() => {
  if (isAdmin.value) return boards.value;
  return boards.value.filter((board) => board.key !== 'notice');
});
const showBoardPicker = computed(() => writableBoards.value.length > 1);

const activeFlairKey = computed(() => {
  if (form.value.flair_tag === FLAIR_OTHER) return FLAIR_OTHER;
  if (form.value.platform_id) return String(form.value.platform_id);
  return 'none';
});

function selectBoard(boardKey) {
  form.value.board = boardKey;
  if (boardKey !== 'ott') {
    form.value.platform_id = null;
    form.value.flair_tag = '';
  }
}

function normalizeBoardSelection() {
  const requestedBoard = boards.value.find((board) => board.key === form.value.board);
  if (!requestedBoard || (requestedBoard.key === 'notice' && !isAdmin.value)) {
    form.value.board = 'ott';
  }
  if (form.value.board !== 'ott') {
    form.value.platform_id = null;
    form.value.flair_tag = '';
  }
}

function selectFlair(key) {
  if (key === 'none') {
    form.value.platform_id = null;
    form.value.flair_tag = '';
    return;
  }
  if (key === FLAIR_OTHER) {
    form.value.platform_id = null;
    form.value.flair_tag = FLAIR_OTHER;
    return;
  }
  form.value.platform_id = Number(key);
  form.value.flair_tag = '';
}

async function loadBoards() {
  boards.value = await fetchCommunityBoards();
  normalizeBoardSelection();
}

async function loadPlatforms() {
  try {
    const payload = await fetchBenchmarkLeaderboard();
    platforms.value = payload?.platforms || [];
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
  submitting.value = true;
  try {
    const payload = {
      board: form.value.board,
      title: form.value.title,
      content: form.value.content,
    };
    if (form.value.board === 'ott') {
      if (form.value.platform_id) payload.platform_id = form.value.platform_id;
      if (form.value.flair_tag) payload.flair_tag = form.value.flair_tag;
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
        <div v-if="showBoardPicker" class="field">
          <label>게시판</label>
          <div class="board-picker">
            <button
              v-for="board in writableBoards"
              :key="board.key"
              type="button"
              class="board-pick"
              :class="{ active: form.board === board.key, notice: board.key === 'notice' }"
              @click="selectBoard(board.key)"
            >
              {{ board.name }}
            </button>
          </div>
          <p v-if="form.board === 'notice'" class="muted">공지사항은 관리자만 작성할 수 있으며, 다른 게시판 상단에 고정 표시됩니다.</p>
        </div>
        <div v-else class="board-chip">
          <span>게시판</span>
          <strong>{{ activeBoard?.name || '게시판' }}</strong>
        </div>

        <div v-if="showPlatformPicker" class="field">
          <label>플레어 <span class="optional">(선택)</span></label>
          <div class="flair-picker">
            <CommunityFlair
              label="없음"
              platform-name=""
              selectable
              :selected="activeFlairKey === 'none'"
              @select="selectFlair('none')"
            />
            <CommunityFlair
              v-for="platform in platforms"
              :key="platform.platform_id"
              :label="platform.name"
              :platform-name="platform.name"
              selectable
              :selected="activeFlairKey === String(platform.platform_id)"
              @select="selectFlair(String(platform.platform_id))"
            />
            <CommunityFlair
              label="기타"
              flair-tag="other"
              selectable
              :selected="activeFlairKey === FLAIR_OTHER"
              @select="selectFlair(FLAIR_OTHER)"
            />
          </div>
          <p class="muted">플레어는 선택 사항입니다. 서비스별 색상 태그로 글 주제를 표시할 수 있습니다.</p>
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

.board-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.board-pick {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--ws-border);
  border-radius: 999px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.board-pick.active {
  border-color: rgba(var(--ws-primary-rgb), 0.45);
  background: rgba(var(--ws-primary-rgb), 0.14);
  color: var(--ws-primary);
}

.board-pick.notice.active {
  border-color: rgba(251, 191, 36, 0.55);
  background: rgba(180, 83, 9, 0.18);
  color: #fbbf24;
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

.optional {
  font-weight: 700;
  color: var(--ws-muted);
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

.flair-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.write-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
