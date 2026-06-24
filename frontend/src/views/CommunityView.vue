<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { fetchCommunityBoards, fetchCommunityPosts } from '../api/community';
import { fetchSubscriptionPlatforms } from '../api/subscriptions';
import { profileInitial } from '../utils/formatters';
import { useSessionStore } from '../stores/session';
import PageHeader from '../components/PageHeader.vue';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const boards = ref([]);
const selectedBoard = ref(typeof route.query.board === 'string' ? route.query.board : 'ott');
const platformFilterId = ref(route.query.platform_id ? String(route.query.platform_id) : '');
const posts = ref([]);
const notices = ref([]);
const loading = ref(false);
const error = ref('');

const isAdmin = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const activeBoard = computed(() => boards.value.find((board) => board.key === selectedBoard.value));
const currentPosts = computed(() => posts.value);
const showPinnedNotices = computed(() => selectedBoard.value !== 'notice' && notices.value.length > 0);
const canWriteCurrentBoard = computed(() => selectedBoard.value !== 'notice' || isAdmin.value);
const platformFilterName = ref('');
const platformFlairName = computed(() => {
  if (selectedBoard.value !== 'ott' || !platformFilterId.value) return '';
  if (platformFilterName.value) return platformFilterName.value;
  const match = posts.value.find((post) => String(post.platform_id) === platformFilterId.value);
  return match?.platform_name || '';
});

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' });
}

function goWrite() {
  if (!session.isAuthenticated) {
    alert('로그인 후 글을 작성할 수 있습니다.');
    router.push('/login');
    return;
  }
  if (!canWriteCurrentBoard.value) return;
  const query = { board: selectedBoard.value };
  if (selectedBoard.value === 'ott' && platformFilterId.value) {
    query.platform_id = platformFilterId.value;
  }
  router.push({ path: '/community/write', query });
}

async function loadBoards() {
  boards.value = await fetchCommunityBoards();
}

async function loadPlatformFilterName() {
  if (!platformFilterId.value) {
    platformFilterName.value = '';
    return;
  }
  try {
    const platforms = await fetchSubscriptionPlatforms();
    const match = platforms.find((item) => String(item.id) === platformFilterId.value);
    platformFilterName.value = match?.name || '';
  } catch {
    platformFilterName.value = '';
  }
}

async function loadNotices() {
  const data = await fetchCommunityPosts({ board: 'notice' });
  notices.value = data.results || [];
}

async function loadPosts(board = selectedBoard.value) {
  selectedBoard.value = board;
  loading.value = true;
  error.value = '';
  try {
    const data = await fetchCommunityPosts({
      board,
      platformId: board === 'ott' ? platformFilterId.value : '',
    });
    posts.value = data.results || [];
  } catch (err) {
    posts.value = [];
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function clearPlatformFilter() {
  platformFilterId.value = '';
  router.replace({ path: '/community', query: { board: selectedBoard.value } });
  loadPosts(selectedBoard.value);
}

onMounted(async () => {
  await loadBoards();
  await loadPlatformFilterName();
  await Promise.all([loadPosts(selectedBoard.value), loadNotices()]);
});
</script>

<template>
  <main>
    <PageHeader
      eyebrow="Community"
      title="커뮤니티"
      description="OTT 가성비, 추천 콘텐츠, 영화와 시리즈 이야기를 나누는 공간입니다."
    />

    <nav class="board-nav" aria-label="게시판 선택">
      <button
        v-for="board in boards"
        :key="board.key"
        class="board-nav-item"
        :class="{ active: selectedBoard === board.key }"
        type="button"
        @click="loadPosts(board.key)"
      >
        {{ board.name }}
      </button>
    </nav>

    <section class="panel post-list-panel">
      <div class="board-heading">
        <div>
          <h2>{{ activeBoard?.name || '게시판' }}</h2>
          <p class="muted">{{ activeBoard?.description }}</p>
          <p v-if="platformFlairName" class="platform-filter-chip">
            <span class="flair">{{ platformFlairName }}</span> 플랫폼 글만 보는 중
            <button type="button" class="link-btn" @click="clearPlatformFilter">필터 해제</button>
          </p>
        </div>
        <button v-if="canWriteCurrentBoard" class="button primary" type="button" @click="goWrite">글쓰기</button>
      </div>

      <p v-if="error" class="notice">{{ error }}</p>
      <div v-else-if="loading" class="loader">게시글을 불러오는 중입니다.</div>
      <div v-else class="board-list">
        <RouterLink v-for="notice in showPinnedNotices ? notices.slice(0, 3) : []" :key="`notice-${notice.id}`" class="board-row notice-row" :to="`/community/${notice.id}`">
          <span class="row-board">공지</span>
          <strong class="row-title">{{ notice.title }}</strong>
          <span class="row-author author-chip">
            <img v-if="notice.author.profile_image" :src="notice.author.profile_image" alt="" />
            <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
              {{ profileInitial(notice.author.nickname) }}
            </span>
            <span>{{ notice.author.nickname }}</span>
          </span>
          <span class="row-date">{{ formatDate(notice.created_at) }}</span>
          <span class="row-count">{{ notice.view_count }}</span>
          <span class="row-count">{{ notice.comment_count }}</span>
        </RouterLink>

        <div v-if="currentPosts.length === 0" class="empty">아직 게시글이 없습니다.</div>
        <RouterLink v-for="post in currentPosts" :key="post.id" class="board-row" :to="`/community/${post.id}`">
          <span class="row-board">
            <span v-if="post.is_notice" class="flair notice">공지</span>
            <span v-else-if="post.platform_name" class="flair">{{ post.platform_name }}</span>
            <span v-else>{{ post.board_label }}</span>
          </span>
          <strong class="row-title">{{ post.title }}</strong>
          <span class="row-author author-chip">
            <img v-if="post.author.profile_image" :src="post.author.profile_image" alt="" />
            <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
              {{ profileInitial(post.author.nickname) }}
            </span>
            <span>{{ post.author.nickname }}</span>
          </span>
          <span class="row-date">{{ formatDate(post.created_at) }}</span>
          <span class="row-count">{{ post.view_count }}</span>
          <span class="row-count">{{ post.comment_count }}</span>
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.board-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: 14px;
  border-bottom: 2px solid var(--ws-border);
}

.board-nav-item {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid var(--ws-border);
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
  background: var(--ws-surface-2);
  color: var(--ws-muted);
  cursor: pointer;
  font-weight: 900;
}

.board-nav-item + .board-nav-item {
  margin-left: -1px;
}

.board-nav-item.active {
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
  border-color: var(--ws-primary);
}

.post-list-panel h2 {
  font-size: 20px;
}

.board-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.board-list {
  overflow: hidden;
  border-top: 2px solid var(--ws-border);
}

.board-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) 120px 76px 58px 58px;
  gap: 10px;
  align-items: center;
  min-height: 44px;
  padding: 9px 10px;
  border-bottom: 1px solid var(--ws-border);
  background: var(--ws-surface);
  color: var(--ws-text);
}

.board-row:hover {
  background: rgba(217, 221, 146, 0.04);
}

.notice-row {
  background: rgba(252, 163, 17, 0.08);
}

.row-board {
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 900;
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

.flair.notice {
  background: rgba(252, 163, 17, 0.2);
  color: var(--ws-secondary);
}

.platform-filter-chip {
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}

.link-btn {
  border: none;
  background: none;
  color: var(--ws-muted);
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
  padding: 0;
}

.notice-row .row-board {
  color: var(--ws-secondary);
}

.row-title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 14px;
}

.row-author,
.row-date,
.row-count {
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 800;
  text-align: right;
}

.row-author {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.empty {
  border-bottom: 1px solid var(--ws-border);
}

.author-chip {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-width: 0;
}

.author-chip img,
.default-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex: none;
  border: none;
  box-shadow: none;
}

.author-chip img {
  object-fit: cover;
}

.author-chip .avatar-initial-letter {
  font-size: 11px;
}

@media (max-width: 820px) {
  .board-heading,
  .board-row {
    grid-template-columns: 1fr;
  }

  .board-heading {
    align-items: stretch;
  }

  .board-row {
    gap: 4px;
  }

  .row-author,
  .row-date,
  .row-count {
    text-align: left;
  }
}
</style>
