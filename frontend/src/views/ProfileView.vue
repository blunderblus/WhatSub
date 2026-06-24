<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { fetchMyCommunityPosts } from '../api/community';
import { apiRequest } from '../api/http';
import PageHeader from '../components/PageHeader.vue';
import UserSubscriptionDashboard from '../components/UserSubscriptionDashboard.vue';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const activeTab = ref('subscriptions');
const form = ref({ nickname: '', profile_image: '' });
const message = ref('');
const error = ref('');
const saving = ref(false);
const myPosts = ref([]);
const myPostsLoading = ref(false);
const myPostsError = ref('');
const avatarPresetGroups = [
  {
    title: '3D 기본 프사',
    avatars: Array.from({ length: 9 }, (_, index) => ({
      src: `/img/avatars/avatar-3d-${String(index + 1).padStart(2, '0')}.png`,
      label: `3D 아바타 ${index + 1}`,
    })),
  },
  {
    title: '2D 아이콘 프사',
    avatars: [
      { src: '/img/avatars/avatar-2d-blue.svg', label: '블루 아이콘' },
      { src: '/img/avatars/avatar-2d-pink.svg', label: '핑크 아이콘' },
      { src: '/img/avatars/avatar-2d-mint.svg', label: '민트 아이콘' },
      { src: '/img/avatars/avatar-2d-bot.svg', label: '봇 아이콘' },
    ],
  },
];

const profileName = computed(() => session.user?.nickname || session.user?.username || '내 프로필');
const profileInitial = computed(() => profileName.value.charAt(0).toUpperCase());

function hydrateForm() {
  form.value.nickname = session.user?.nickname || session.user?.username || '';
  form.value.profile_image = session.user?.profile_image || '';
}

function switchTab(tab) {
  activeTab.value = tab;
  if (tab === 'posts' && !myPosts.value.length && !myPostsLoading.value) {
    loadMyPosts();
  }
}

function selectAvatar(src) {
  form.value.profile_image = src;
}

async function loadMyPosts() {
  myPostsLoading.value = true;
  myPostsError.value = '';
  try {
    const boards = ['ott', 'free', 'notice'];
    const responses = await Promise.all(boards.map((board) => fetchMyCommunityPosts({ board })));
    myPosts.value = responses
      .flatMap((response) => response.results || [])
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (err) {
    myPostsError.value = err.message;
    myPosts.value = [];
  } finally {
    myPostsLoading.value = false;
  }
}

async function submit() {
  message.value = '';
  error.value = '';
  saving.value = true;
  try {
    const data = await apiRequest('/api/accounts/profile/', {
      method: 'PATCH',
      body: form.value,
    });
    session.user = data.user;
    hydrateForm();
    message.value = '저장되었습니다.';
  } catch (err) {
    error.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  hydrateForm();
});
</script>

<template>
  <main class="profile-page">
    <PageHeader eyebrow="My Space" title="내 대시보드" />

    <section class="profile-hero panel">
      <div class="profile-avatar-frame">
        <img v-if="form.profile_image" :src="form.profile_image" alt="" />
        <span v-else class="default-avatar" aria-hidden="true">{{ profileInitial }}</span>
      </div>
      <div class="profile-copy">
        <strong>{{ profileName }}</strong>
        <span>{{ session.user?.email || '이메일 정보 없음' }}</span>
      </div>
    </section>

    <nav class="profile-tabs" aria-label="프로필 탭" role="tablist">
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'subscriptions'"
        :class="{ active: activeTab === 'subscriptions' }"
        @click="switchTab('subscriptions')"
      >
        내 구독
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'posts'"
        :class="{ active: activeTab === 'posts' }"
        @click="switchTab('posts')"
      >
        내가 쓴 글
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'settings'"
        :class="{ active: activeTab === 'settings' }"
        @click="switchTab('settings')"
      >
        프로필 설정
      </button>
    </nav>

    <UserSubscriptionDashboard v-if="activeTab === 'subscriptions'" />

    <section v-else-if="activeTab === 'posts'" class="panel my-posts-panel">
      <div class="section-head">
        <div>
          <h2>내가 쓴 글</h2>
          <p class="muted small">커뮤니티에 남긴 글을 모아봅니다.</p>
        </div>
        <RouterLink class="button primary" to="/community/write">글쓰기</RouterLink>
      </div>

      <p v-if="myPostsError" class="notice">{{ myPostsError }}</p>
      <div v-else-if="myPostsLoading" class="loader">내 글을 불러오는 중입니다.</div>
      <div v-else-if="myPosts.length" class="post-list">
        <RouterLink v-for="post in myPosts" :key="post.id" class="post-row" :to="`/community/${post.id}`">
          <div>
            <span class="board-label">{{ post.board_label }}</span>
            <strong>{{ post.title }}</strong>
            <p>{{ post.content }}</p>
          </div>
          <div class="post-meta">
            <span>댓글 {{ post.comment_count }}</span>
            <span>조회 {{ post.view_count }}</span>
          </div>
        </RouterLink>
      </div>
      <div v-else class="empty">
        아직 작성한 글이 없습니다.
        <RouterLink class="button primary" to="/community/write">첫 글 쓰기</RouterLink>
      </div>
    </section>

    <section v-else class="form-card profile-card">
      <p class="eyebrow">Profile</p>
      <h2>프로필 설정</h2>
      <p class="muted">커뮤니티에서 보여줄 닉네임을 설정합니다.</p>

      <p v-if="message" class="notice success">{{ message }}</p>
      <p v-if="error" class="notice">{{ error }}</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label for="nickname">닉네임</label>
          <input id="nickname" v-model.trim="form.nickname" maxlength="30" required />
        </div>
        <div class="avatar-presets">
          <div
            v-for="group in avatarPresetGroups"
            :key="group.title"
            class="avatar-preset-group"
          >
            <h3>{{ group.title }}</h3>
            <div class="avatar-grid">
              <button
                v-for="avatar in group.avatars"
                :key="avatar.src"
                type="button"
                class="avatar-option"
                :class="{ selected: form.profile_image === avatar.src }"
                :aria-label="avatar.label"
                :aria-pressed="form.profile_image === avatar.src"
                @click="selectAvatar(avatar.src)"
              >
                <img :src="avatar.src" :alt="avatar.label" />
              </button>
            </div>
          </div>
        </div>
        <div class="field">
          <label for="profile_image">프로필 이미지 URL 또는 기본 이미지 경로</label>
          <input id="profile_image" v-model.trim="form.profile_image" type="text" placeholder="https://... 또는 /img/avatars/..." />
        </div>
        <button class="button primary full-width" style="margin-top: 22px" type="submit" :disabled="saving">
          {{ saving ? '저장 중' : '저장하기' }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.profile-page {
  display: grid;
  gap: 28px;
}

.profile-hero {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  min-height: 82px;
}

.profile-avatar-frame {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
}

.profile-avatar-frame img,
.profile-avatar-frame .default-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  flex: none;
}

.profile-avatar-frame img {
  display: block;
  object-fit: cover;
  object-position: center;
}

.default-avatar {
  display: grid;
  place-items: center;
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
  font-size: 22px;
  font-weight: 900;
}

.profile-hero strong,
.profile-hero span {
  display: block;
}

.profile-copy {
  min-width: 0;
  align-self: center;
}

.profile-copy strong {
  line-height: 1.2;
}

.profile-hero span {
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  margin-top: 3px;
  overflow-wrap: anywhere;
}

.profile-tabs {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(112px, 1fr));
  gap: 4px;
  justify-self: start;
  padding: 5px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.28);
  border-radius: 8px;
  background: linear-gradient(135deg, #141414, rgba(var(--ws-secondary-rgb), 0.16));
  box-shadow: 0 10px 24px rgba(var(--ws-secondary-rgb), 0.12);
  margin-top: 4px;
  margin-bottom: 4px;
}

.profile-tabs button {
  min-height: 40px;
  padding: 0 16px;
  border: none;
  background: transparent;
  color: #e5e7eb;
  cursor: pointer;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 900;
  line-height: 1;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.profile-tabs button.active {
  background: linear-gradient(135deg, var(--ws-primary), var(--ws-secondary));
  color: #141414;
  box-shadow: 0 5px 14px rgba(var(--ws-secondary-rgb), 0.26);
}

.profile-tabs button:not(.active):hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.profile-tabs button:focus-visible {
  outline: 2px solid var(--ws-secondary);
  outline-offset: 2px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2 {
  margin: 0 0 4px;
}

.post-list {
  display: grid;
  gap: 10px;
}

.post-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  color: inherit;
  text-decoration: none;
}

.post-row:hover {
  border-color: var(--ws-primary);
  background: var(--ws-surface-2);
}

.post-row strong,
.post-row p {
  display: block;
  margin: 4px 0 0;
}

.post-row p {
  overflow: hidden;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.board-label {
  color: var(--ws-secondary);
  font-size: 12px;
  font-weight: 900;
}

.post-meta {
  display: grid;
  gap: 4px;
  justify-items: end;
  color: var(--ws-muted);
  font-size: 12px;
  font-weight: 800;
}

.profile-card {
  max-width: 620px;
  margin: 0;
}

.avatar-presets {
  display: grid;
  gap: 18px;
  margin: 20px 0;
  padding: 16px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.avatar-preset-group {
  display: grid;
  gap: 10px;
}

.avatar-preset-group h3 {
  margin: 0;
  color: var(--ws-secondary);
  font-size: 14px;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(58px, 1fr));
  gap: 10px;
}

.avatar-option {
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
}

.avatar-option:hover {
  border-color: var(--ws-secondary);
  background: rgba(var(--ws-secondary-rgb), 0.12);
  transform: translateY(-1px);
}

.avatar-option.selected {
  border-color: var(--ws-primary);
  background: linear-gradient(135deg, rgba(var(--ws-primary-rgb), 0.18), rgba(var(--ws-secondary-rgb), 0.2));
}

.avatar-option img {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.success {
  border-color: rgba(217, 221, 146, 0.35);
  background: rgba(217, 221, 146, 0.08);
  color: var(--ws-primary);
}

@media (max-width: 640px) {
  .profile-tabs {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .section-head,
  .post-row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .post-meta {
    justify-items: start;
  }
}
</style>
