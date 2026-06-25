<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { fetchMyCommunityPosts } from '../api/community';
import { apiRequest } from '../api/http';
import PageHeader from '../components/PageHeader.vue';
import UserSubscriptionDashboard from '../components/UserSubscriptionDashboard.vue';
import { profileInitial as getProfileInitial } from '../utils/formatters';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const router = useRouter();
const activeTab = ref('subscriptions');
const form = ref({ nickname: '', profile_image: '', bio: '' });
const withdrawPassword = ref('');
const withdrawConfirmed = ref(false);
const withdrawing = ref(false);
const withdrawError = ref('');
const message = ref('');
const error = ref('');
const saving = ref(false);
const myPosts = ref([]);
const myPostsLoading = ref(false);
const myPostsError = ref('');
const avatarPresets = Array.from({ length: 9 }, (_, index) => ({
  src: `/img/avatars/avatar-3d-${String(index + 1).padStart(2, '0')}.png`,
  label: `기본 프사 ${index + 1}`,
}));

const profileName = computed(() => session.user?.nickname || session.user?.username || '내 프로필');
const profileInitial = computed(() => getProfileInitial(profileName.value));
const isStaffAccount = computed(() => Boolean(session.user?.is_staff || session.user?.is_superuser));
const requiresWithdrawPassword = computed(() => session.user?.has_password !== false);

function hydrateForm() {
  form.value.nickname = session.user?.nickname || session.user?.username || '';
  form.value.profile_image = session.user?.profile_image || '';
  form.value.bio = session.user?.bio || '';
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

async function submitWithdraw() {
  withdrawError.value = '';
  if (!withdrawConfirmed.value) {
    withdrawError.value = '탈퇴 안내를 확인해 주세요.';
    return;
  }
  if (requiresWithdrawPassword.value && !withdrawPassword.value) {
    withdrawError.value = '비밀번호를 입력해 주세요.';
    return;
  }
  if (!window.confirm('정말 탈퇴하시겠습니까? 삭제된 데이터는 복구할 수 없습니다.')) {
    return;
  }

  withdrawing.value = true;
  try {
    const payload = requiresWithdrawPassword.value ? { password: withdrawPassword.value } : {};
    await session.withdraw(payload);
    alert('회원 탈퇴가 완료되었습니다.');
    router.push('/');
  } catch (err) {
    withdrawError.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
  } finally {
    withdrawing.value = false;
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
        <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">{{ profileInitial }}</span>
      </div>
      <div class="profile-copy">
        <strong>{{ profileName }}</strong>
        <span>{{ session.user?.email || '이메일 정보 없음' }}</span>
        <div v-if="session.user?.taste_titles?.habit || session.user?.taste_titles?.genre" class="taste-title-row">
          <span v-if="session.user?.taste_titles?.habit" class="taste-title habit">{{ session.user.taste_titles.habit }}</span>
          <span v-if="session.user?.taste_titles?.genre" class="taste-title genre">{{ session.user.taste_titles.genre }}</span>
        </div>
        <p v-if="session.user?.taste_summary" class="taste-summary">{{ session.user.taste_summary }}</p>
        <p v-if="form.bio" class="intro-text">{{ form.bio }}</p>
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
          <h3>기본 프사</h3>
          <div class="avatar-grid">
            <button
              type="button"
              class="avatar-option avatar-option-initial avatar-initial-letter"
              :class="{ selected: !form.profile_image }"
              aria-label="닉네임 이니셜"
              :aria-pressed="!form.profile_image"
              @click="selectAvatar('')"
            >
              {{ profileInitial }}
            </button>
            <button
              v-for="avatar in avatarPresets"
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
        <div class="field">
          <label for="profile_image">프로필 이미지 URL 또는 기본 이미지 경로</label>
          <input id="profile_image" v-model.trim="form.profile_image" type="text" placeholder="https://... 또는 /img/avatars/..." />
        </div>
        <div class="field">
          <label for="bio">소개글</label>
          <textarea
            id="bio"
            v-model.trim="form.bio"
            maxlength="200"
            rows="4"
            placeholder="나를 소개하는 한 줄 (최대 200자)"
          />
        </div>
        <button class="button primary full-width" style="margin-top: 22px" type="submit" :disabled="saving">
          {{ saving ? '저장 중' : '저장하기' }}
        </button>
      </form>

      <section v-if="!isStaffAccount" class="withdraw-section">
        <h3>회원 탈퇴</h3>
        <p class="muted small">
          탈퇴 시 구독 정보, 취향 프로필, 커뮤니티 글·댓글, 리뷰·반응 등 계정과 연결된 데이터가 모두 삭제됩니다.
        </p>
        <p v-if="withdrawError" class="notice">{{ withdrawError }}</p>
        <div v-if="requiresWithdrawPassword" class="field">
          <label for="withdraw_password">비밀번호 확인</label>
          <input
            id="withdraw_password"
            v-model="withdrawPassword"
            type="password"
            autocomplete="current-password"
            placeholder="현재 비밀번호"
          />
        </div>
        <label class="withdraw-confirm">
          <input v-model="withdrawConfirmed" type="checkbox" />
          <span>위 안내를 확인했으며, 탈퇴 후 데이터 복구가 불가능함에 동의합니다.</span>
        </label>
        <button class="button danger full-width" type="button" :disabled="withdrawing" @click="submitWithdraw">
          {{ withdrawing ? '탈퇴 처리 중' : '회원 탈퇴' }}
        </button>
      </section>
      <p v-else class="muted small withdraw-staff-note">관리자 계정은 탈퇴할 수 없습니다.</p>
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
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  flex: none;
}

.profile-avatar-frame img,
.profile-avatar-frame .default-avatar {
  width: 100%;
  height: 100%;
  border: none;
  box-shadow: none;
}

.profile-avatar-frame img {
  display: block;
  object-fit: cover;
  object-position: center;
}

.profile-hero strong {
  display: block;
}

.profile-copy {
  min-width: 0;
  align-self: center;
}

.profile-copy strong {
  line-height: 1.2;
}

.profile-copy > span {
  display: block;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  margin-top: 3px;
  overflow-wrap: anywhere;
}

.taste-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.taste-title {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}

.taste-title.habit {
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.35);
  background: rgba(var(--ws-secondary-rgb), 0.12);
  color: var(--ws-secondary);
}

.taste-title.genre {
  border: 1px solid rgba(var(--ws-primary-rgb), 0.35);
  background: rgba(var(--ws-primary-rgb), 0.12);
  color: var(--ws-primary);
}

.taste-summary {
  margin: 8px 0 0;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.45;
}

.intro-text {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ws-text);
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

.profile-avatar-frame .avatar-initial-letter {
  font-size: 24px;
}

.avatar-presets {
  display: grid;
  gap: 12px;
  margin: 20px 0;
  padding: 16px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.avatar-presets h3 {
  margin: 0;
  color: var(--ws-secondary);
  font-size: 14px;
}

.avatar-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.avatar-option {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  padding: 0;
  border: none;
  border-radius: 50%;
  overflow: hidden;
  background: var(--ws-surface-2);
  cursor: pointer;
  transition: transform 0.15s ease, filter 0.15s ease, opacity 0.15s ease;
}

.avatar-option:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.avatar-option.selected {
  filter: brightness(1.12);
  transform: scale(1.04);
}

.avatar-option img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border: none;
}

.avatar-option-initial.avatar-initial-letter {
  font-size: 24px;
  background: var(--ws-primary);
}

.success {
  border-color: rgba(217, 221, 146, 0.35);
  background: rgba(217, 221, 146, 0.08);
  color: var(--ws-primary);
}

.withdraw-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: grid;
  gap: 12px;
}

.withdraw-section h3 {
  margin: 0;
  color: #fca5a5;
  font-size: 16px;
}

.withdraw-confirm {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
}

.withdraw-confirm input {
  margin-top: 3px;
}

.button.danger {
  background: linear-gradient(135deg, #7f1d1d, #b91c1c);
  color: #fff;
}

.button.danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.withdraw-staff-note {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
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
