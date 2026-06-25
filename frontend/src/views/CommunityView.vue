<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { fetchCommunityBoards, fetchCommunityPosts } from '../api/community';
import { fetchBenchmarkLeaderboard } from '../api/benchmark';
import { profileInitial } from '../utils/formatters';
import { FLAIR_OTHER } from '../utils/platformFlair';
import { useSessionStore } from '../stores/session';
import PageHeader from '../components/PageHeader.vue';
import CommunityFlair from '../components/CommunityFlair.vue';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const boards = ref([]);
const selectedBoard = ref(typeof route.query.board === 'string' ? route.query.board : 'ott');
const flairFilter = ref(resolveFlairFilterFromRoute());
const searchInput = ref(typeof route.query.q === 'string' ? route.query.q : '');
const appliedSearch = ref(searchInput.value);
const flairPlatforms = ref([]);
const posts = ref([]);
const notices = ref([]);
const loading = ref(false);
const error = ref('');

const isAdmin = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const activeBoard = computed(() => boards.value.find((board) => board.key === selectedBoard.value));
const currentPosts = computed(() => posts.value);
const showPinnedNotices = computed(() => selectedBoard.value !== 'notice' && notices.value.length > 0 && !appliedSearch.value);
const canWriteCurrentBoard = computed(() => selectedBoard.value !== 'notice' || isAdmin.value);
const showOttFilters = computed(() => selectedBoard.value === 'ott');
const hasActiveFilters = computed(() => flairFilter.value !== 'all' || Boolean(appliedSearch.value));

function resolveFlairFilterFromRoute() {
  if (route.query.no_flair === '1') return 'none';
  if (route.query.flair_tag === FLAIR_OTHER) return FLAIR_OTHER;
  if (route.query.platform_id) return String(route.query.platform_id);
  return 'all';
}

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' });
}

function flairFilterParams() {
  if (flairFilter.value === 'none') return { noFlair: true };
  if (flairFilter.value === FLAIR_OTHER) return { flairTag: FLAIR_OTHER };
  if (flairFilter.value !== 'all') return { platformId: flairFilter.value };
  return {};
}

function syncRouteQuery() {
  const query = { board: selectedBoard.value };
  if (appliedSearch.value) query.q = appliedSearch.value;
  if (flairFilter.value === 'none') query.no_flair = '1';
  else if (flairFilter.value === FLAIR_OTHER) query.flair_tag = FLAIR_OTHER;
  else if (flairFilter.value !== 'all') query.platform_id = flairFilter.value;
  router.replace({ path: '/community', query });
}

function goWriteNotice() {
  if (!session.isAuthenticated) {
    alert('로그인 후 공지를 작성할 수 있습니다.');
    router.push('/login');
    return;
  }
  if (!isAdmin.value) return;
  router.push({ path: '/community/write', query: { board: 'notice' } });
}

function goWrite() {
  if (!session.isAuthenticated) {
    alert('로그인 후 글을 작성할 수 있습니다.');
    router.push('/login');
    return;
  }
  if (!canWriteCurrentBoard.value) return;
  const query = { board: selectedBoard.value };
  if (flairFilter.value !== 'all' && flairFilter.value !== 'none' && flairFilter.value !== FLAIR_OTHER) {
    query.platform_id = flairFilter.value;
  }
  router.push({ path: '/community/write', query });
}

async function loadBoards() {
  boards.value = await fetchCommunityBoards();
}

async function loadFlairPlatforms() {
  try {
    const payload = await fetchBenchmarkLeaderboard();
    flairPlatforms.value = payload?.platforms || [];
  } catch {
    flairPlatforms.value = [];
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
      q: appliedSearch.value,
      ...(board === 'ott' ? flairFilterParams() : {}),
    });
    posts.value = data.results || [];
  } catch (err) {
    posts.value = [];
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function selectFlairFilter(key) {
  flairFilter.value = key;
  syncRouteQuery();
  loadPosts();
}

function submitSearch() {
  appliedSearch.value = searchInput.value.trim();
  syncRouteQuery();
  loadPosts();
}

function clearFilters() {
  flairFilter.value = 'all';
  searchInput.value = '';
  appliedSearch.value = '';
  syncRouteQuery();
  loadPosts();
}

watch(() => route.query.board, (board) => {
  if (typeof board === 'string' && board !== selectedBoard.value) {
    loadPosts(board);
  }
});

onMounted(async () => {
  await Promise.all([loadBoards(), loadFlairPlatforms()]);
  await Promise.all([loadPosts(selectedBoard.value), loadNotices()]);
});
</script>

<template>
  <main class="ws-page">
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
      <div class="board-toolbar">
        <form class="search-form" @submit.prevent="submitSearch">
          <input
            v-model="searchInput"
            type="search"
            placeholder="제목, 내용, 작성자 검색"
            aria-label="게시글 검색"
          />
          <button class="button" type="submit">검색</button>
        </form>
        <button v-if="hasActiveFilters" class="button linkish" type="button" @click="clearFilters">필터 초기화</button>
      </div>

      <div v-if="showOttFilters" class="flair-filter-bar" aria-label="플레어 필터">
        <CommunityFlair
          label="전체"
          selectable
          compact
          :selected="flairFilter === 'all'"
          @select="selectFlairFilter('all')"
        />
        <CommunityFlair
          label="없음"
          selectable
          compact
          :selected="flairFilter === 'none'"
          @select="selectFlairFilter('none')"
        />
        <CommunityFlair
          v-for="platform in flairPlatforms"
          :key="platform.platform_id"
          :label="platform.name"
          :platform-name="platform.name"
          selectable
          compact
          :selected="flairFilter === String(platform.platform_id)"
          @select="selectFlairFilter(String(platform.platform_id))"
        />
        <CommunityFlair
          label="기타"
          flair-tag="other"
          selectable
          compact
          :selected="flairFilter === FLAIR_OTHER"
          @select="selectFlairFilter(FLAIR_OTHER)"
        />
      </div>

      <div class="board-heading">
        <div>
          <h2>{{ activeBoard?.name || '게시판' }}</h2>
          <p class="muted">{{ activeBoard?.description }}</p>
        </div>
        <div class="board-actions">
          <button v-if="isAdmin" class="button notice-write" type="button" @click="goWriteNotice">공지 작성</button>
          <button v-if="canWriteCurrentBoard" class="button primary" type="button" @click="goWrite">글쓰기</button>
        </div>
      </div>

      <p v-if="error" class="notice">{{ error }}</p>
      <div v-else-if="loading" class="loader">게시글을 불러오는 중입니다.</div>
      <div v-else class="board-list">
        <RouterLink v-for="notice in showPinnedNotices ? notices.slice(0, 3) : []" :key="`notice-${notice.id}`" class="board-row notice-row" :to="`/community/${notice.id}`">
          <span class="row-board"><CommunityFlair is-notice compact /></span>
          <strong class="row-title">{{ notice.title }}</strong>
          <span class="row-author author-chip">
            <img v-if="notice.author.profile_image" :src="notice.author.profile_image" alt="" />
            <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
              {{ profileInitial(notice.author.nickname) }}
            </span>
            <span>{{ notice.author.nickname }}</span>
            <span v-if="notice.author.taste_title" class="taste-badge">{{ notice.author.taste_title }}</span>
          </span>
          <span class="row-date">{{ formatDate(notice.created_at) }}</span>
          <span class="row-count">{{ notice.view_count }}</span>
          <span class="row-count">{{ notice.comment_count }}</span>
        </RouterLink>

        <div v-if="currentPosts.length === 0" class="empty">조건에 맞는 게시글이 없습니다.</div>
        <RouterLink v-for="post in currentPosts" :key="post.id" class="board-row" :to="`/community/${post.id}`">
          <span class="row-board">
            <CommunityFlair v-if="post.is_notice" is-notice compact />
            <CommunityFlair
              v-else-if="post.flair_label"
              :label="post.flair_label"
              :platform-name="post.platform_name"
              :flair-tag="post.flair_tag"
              compact
            />
            <span v-else>{{ post.board_label }}</span>
          </span>
          <strong class="row-title">{{ post.title }}</strong>
          <span class="row-author author-chip">
            <img v-if="post.author.profile_image" :src="post.author.profile_image" alt="" />
            <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
              {{ profileInitial(post.author.nickname) }}
            </span>
            <span>{{ post.author.nickname }}</span>
            <span v-if="post.author.taste_title" class="taste-badge">{{ post.author.taste_title }}</span>
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
  gap: 6px;
  margin-bottom: 14px;
  padding: 6px;
  border: 1px solid var(--ws-glass-border);
  border-radius: var(--ws-radius-pill);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: var(--ws-glass-highlight);
}

.board-nav-item {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid transparent;
  border-radius: var(--ws-radius-pill);
  background: transparent;
  color: var(--ws-muted);
  cursor: pointer;
  font-weight: 900;
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}

.board-nav-item + .board-nav-item {
  margin-left: 0;
}

.board-nav-item.active {
  background: linear-gradient(135deg, rgba(var(--ws-primary-rgb), 0.92), rgba(var(--ws-secondary-rgb), 0.78));
  color: var(--ws-primary-fg);
  border-color: rgba(var(--ws-primary-rgb), 0.35);
  box-shadow: 0 4px 16px rgba(var(--ws-primary-rgb), 0.2);
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

.board-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.notice-write {
  border-color: rgba(251, 191, 36, 0.45);
  color: #fbbf24;
}

.board-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.search-form {
  display: flex;
  flex: 1 1 280px;
  gap: 8px;
}

.search-form input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
}

.button.linkish {
  background: transparent;
  color: var(--ws-muted);
}

.flair-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px;
  border: 1px solid var(--ws-glass-border);
  border-radius: var(--ws-radius-sm);
  background: rgba(255, 255, 255, 0.02);
}

.board-list {
  overflow: hidden;
  border-top: 1px solid var(--ws-glass-border);
  border-radius: var(--ws-radius-sm);
}

.board-row {
  display: grid;
  grid-template-columns: minmax(0, 112px) minmax(0, 1fr) minmax(0, 120px) 76px 58px 58px;
  gap: 10px;
  align-items: center;
  min-height: 44px;
  padding: 9px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: var(--ws-text);
  transition: background 0.18s, box-shadow 0.18s;
}

.board-row:hover {
  background: rgba(var(--ws-primary-rgb), 0.08);
  box-shadow: var(--ws-glass-highlight);
}

.notice-row {
  background: rgba(252, 163, 17, 0.1);
}

.row-board {
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  font-size: 12px;
  font-weight: 900;
}

.row-board :deep(.community-flair) {
  max-width: 100%;
}

.row-board > span:not(.community-flair) {
  color: var(--ws-primary);
}

.flair {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: rgba(var(--ws-primary-rgb), 0.16);
  border: 1px solid rgba(var(--ws-primary-rgb), 0.28);
  color: var(--ws-primary);
  backdrop-filter: blur(8px);
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
  min-width: 0;
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

.taste-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.35);
  background: rgba(var(--ws-secondary-rgb), 0.14);
  color: var(--ws-secondary);
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
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

@media (min-width: 1280px) {
  .board-row {
    grid-template-columns: minmax(0, 120px) minmax(0, 1fr) minmax(0, 140px) 84px 64px 64px;
    gap: 14px;
    padding-inline: 14px;
  }
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
