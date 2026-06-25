<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import {
  addCommunityComment,
  deleteCommunityComment,
  deleteCommunityPost,
  fetchCommunityPost,
  reportCommunityComment,
  reportCommunityPost,
  updateCommunityCommentReaction,
  updateCommunityPostReaction,
} from '../api/community';
import { profileInitial } from '../utils/formatters';
import CommunityFlair from '../components/CommunityFlair.vue';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const post = ref(null);
const loading = ref(true);
const error = ref('');
const comment = ref('');
const commentMessage = ref('');
const submitting = ref(false);

const isNotice = computed(() => post.value?.board === 'notice');

async function loadPost() {
  loading.value = true;
  error.value = '';
  try {
    post.value = await fetchCommunityPost(route.params.id);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function requireLogin(message) {
  if (session.isAuthenticated) return true;
  alert(message);
  router.push('/login');
  return false;
}

async function reactToPost(reaction) {
  if (post.value?.is_owner) {
    alert('본인 글은 추천 / 비추천할 수 없습니다.');
    return;
  }
  if (!requireLogin('로그인 후 추천할 수 있습니다.')) return;
  const nextReaction = post.value.reactions?.my_reaction === reaction ? null : reaction;
  post.value.reactions = await updateCommunityPostReaction(post.value.id, nextReaction);
}

async function reactToComment(item, reaction) {
  if (item.is_owner) {
    alert('본인 댓글은 추천 / 비추천할 수 없습니다.');
    return;
  }
  if (!requireLogin('로그인 후 추천할 수 있습니다.')) return;
  const nextReaction = item.reactions?.my_reaction === reaction ? null : reaction;
  item.reactions = await updateCommunityCommentReaction(item.id, nextReaction);
}

async function reportPost() {
  if (!requireLogin('로그인 후 신고할 수 있습니다.')) return;
  post.value.reports = await reportCommunityPost(post.value.id);
  alert('신고가 접수되었습니다.');
}

async function reportComment(item) {
  if (!requireLogin('로그인 후 신고할 수 있습니다.')) return;
  item.reports = await reportCommunityComment(item.id);
  alert('신고가 접수되었습니다.');
}

async function addComment() {
  commentMessage.value = '';
  if (!requireLogin('로그인 후 댓글을 작성할 수 있습니다.')) return;

  submitting.value = true;
  try {
    post.value = await addCommunityComment(route.params.id, comment.value);
    comment.value = '';
  } catch (err) {
    commentMessage.value = err.message;
  } finally {
    submitting.value = false;
  }
}

async function deletePost() {
  if (!confirm('삭제하시겠습니까?')) return;
  await deleteCommunityPost(route.params.id);
  router.push('/community');
}

async function deleteComment(id) {
  if (!confirm('삭제하시겠습니까?')) return;
  await deleteCommunityComment(id);
  await loadPost();
}

onMounted(loadPost);
</script>

<template>
  <main>
    <RouterLink class="button" to="/community">커뮤니티로</RouterLink>

    <p v-if="error" class="notice" style="margin-top: 18px">{{ error }}</p>
    <div v-else-if="loading" class="loader" style="margin-top: 18px">게시글을 불러오는 중입니다.</div>

    <template v-else-if="post">
      <article class="panel detail-post">
        <div class="detail-head">
          <CommunityFlair v-if="post.is_notice" is-notice />
          <CommunityFlair
            v-else-if="post.flair_label"
            :label="post.flair_label"
            :platform-name="post.platform_name"
            :flair-tag="post.flair_tag"
          />
          <span v-else class="board-badge">{{ post.board_label }}</span>
        </div>
        <h1>{{ post.title }}</h1>
        <div class="detail-meta">
          <span class="author-chip">
            <img v-if="post.author.profile_image" :src="post.author.profile_image" alt="" />
            <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
              {{ profileInitial(post.author.nickname) }}
            </span>
            <strong>{{ post.author.nickname }}</strong>
          </span>
          <span>조회 {{ post.view_count }}</span>
          <span v-if="!isNotice">댓글 {{ post.comments.length }}</span>
        </div>
        <p>{{ post.content }}</p>

        <div class="post-actions">
          <div class="reaction-bar" aria-label="게시글 추천 비추천">
            <button
              class="icon-button reaction"
              :class="{ active: post.reactions?.my_reaction === 'like' }"
              type="button"
              aria-label="추천"
              title="추천"
              @click="reactToPost('like')"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Zm4.4-7.2L12 3.5V9h6.2a2 2 0 0 1 2 2.3l-1.1 7A3 3 0 0 1 16.2 21H9V10.3l2.4-7.5Z" /></svg>
              <span>{{ post.reactions?.like_count || 0 }}</span>
            </button>
            <button
              class="icon-button reaction down"
              :class="{ active: post.reactions?.my_reaction === 'dislike' }"
              type="button"
              aria-label="비추천"
              title="비추천"
              @click="reactToPost('dislike')"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Zm4.4-7.2L12 3.5V9h6.2a2 2 0 0 1 2 2.3l-1.1 7A3 3 0 0 1 16.2 21H9V10.3l2.4-7.5Z" /></svg>
              <span>{{ post.reactions?.dislike_count || 0 }}</span>
            </button>
          </div>

          <div class="moderation-actions">
            <button
              v-if="!post.is_owner"
              class="icon-button report"
              :class="{ active: post.reports?.reported }"
              type="button"
              aria-label="신고"
              title="신고"
              @click="reportPost"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18v-5a5 5 0 0 1 10 0v5M5 21h14M12 3v2M4.2 6.2l1.4 1.4M19.8 6.2l-1.4 1.4M9 18h6" /></svg>
            </button>
            <button
              v-if="post.is_owner"
              class="icon-button danger"
              type="button"
              aria-label="삭제"
              title="삭제"
              @click="deletePost"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
      </article>

      <section v-if="!isNotice" class="panel" style="margin-top: 16px">
        <h2>댓글</h2>
        <form class="comment-form" @submit.prevent="addComment">
          <textarea v-model="comment" rows="3" placeholder="댓글을 입력하세요" aria-label="댓글"></textarea>
          <button class="button primary" type="submit" :disabled="submitting">등록</button>
        </form>
        <p v-if="commentMessage" class="notice compact-notice">{{ commentMessage }}</p>

        <div v-if="post.comments.length" class="comment-list">
          <article v-for="item in post.comments" :key="item.id" class="comment-item">
            <div class="comment-body">
              <span class="author-chip">
                <img v-if="item.author.profile_image" :src="item.author.profile_image" alt="" />
                <span v-else class="default-avatar avatar-initial-letter" aria-hidden="true">
                  {{ profileInitial(item.author.nickname) }}
                </span>
                <strong>{{ item.author.nickname }}</strong>
              </span>
              <p>{{ item.content }}</p>
              <div class="comment-reactions" aria-label="댓글 추천 비추천">
                <button
                  class="icon-button reaction small"
                  :class="{ active: item.reactions?.my_reaction === 'like' }"
                  type="button"
                  aria-label="추천"
                  title="추천"
                  @click="reactToComment(item, 'like')"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Zm4.4-7.2L12 3.5V9h6.2a2 2 0 0 1 2 2.3l-1.1 7A3 3 0 0 1 16.2 21H9V10.3l2.4-7.5Z" /></svg>
                  <span>{{ item.reactions?.like_count || 0 }}</span>
                </button>
                <button
                  class="icon-button reaction small down"
                  :class="{ active: item.reactions?.my_reaction === 'dislike' }"
                  type="button"
                  aria-label="비추천"
                  title="비추천"
                  @click="reactToComment(item, 'dislike')"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Zm4.4-7.2L12 3.5V9h6.2a2 2 0 0 1 2 2.3l-1.1 7A3 3 0 0 1 16.2 21H9V10.3l2.4-7.5Z" /></svg>
                  <span>{{ item.reactions?.dislike_count || 0 }}</span>
                </button>
              </div>
            </div>
            <div class="comment-tools">
              <button
                v-if="!item.is_owner"
                class="icon-button report small-tool"
                :class="{ active: item.reports?.reported }"
                type="button"
                aria-label="신고"
                title="신고"
                @click="reportComment(item)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18v-5a5 5 0 0 1 10 0v5M5 21h14M12 3v2M4.2 6.2l1.4 1.4M19.8 6.2l-1.4 1.4M9 18h6" /></svg>
              </button>
              <button
                v-if="item.is_owner"
                class="icon-button danger small-tool"
                type="button"
                aria-label="삭제"
                title="삭제"
                @click="deleteComment(item.id)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </div>
          </article>
        </div>
        <p v-else class="empty" style="margin-top: 14px">첫 댓글을 남겨보세요.</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail-post {
  margin-top: 18px;
}

.detail-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.board-badge {
  display: inline-flex;
  margin-bottom: 10px;
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(217, 221, 146, 0.12);
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 900;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 800;
}

.detail-post p {
  white-space: pre-wrap;
}

.author-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.author-chip img,
.default-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex: none;
  border: none;
  box-shadow: none;
}

.author-chip img {
  object-fit: cover;
}

.author-chip .avatar-initial-letter {
  font-size: 12px;
}

.post-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}

.reaction-bar,
.comment-reactions,
.moderation-actions,
.comment-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.comment-reactions {
  margin-top: 8px;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  min-width: 36px;
  padding: 0 8px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
}

.icon-button svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
  flex: none;
}

.icon-button.reaction svg {
  fill: currentColor;
  stroke: currentColor;
  stroke-width: 1.5;
}

.icon-button.reaction {
  min-width: 54px;
}

.icon-button.small {
  height: 30px;
  min-width: 48px;
  padding: 0 7px;
}

.icon-button.small-tool,
.icon-button.danger {
  width: 32px;
  min-width: 32px;
  padding: 0;
}

.icon-button.active {
  border-color: var(--ws-primary);
  background: rgba(217, 221, 146, 0.12);
  color: var(--ws-primary);
}

.icon-button.down svg {
  transform: rotate(180deg);
}

.icon-button.report {
  border-color: rgba(252, 163, 17, 0.35);
  background: rgba(252, 163, 17, 0.08);
  color: var(--ws-secondary);
}

.icon-button.report.active {
  border-color: var(--ws-secondary);
  background: rgba(252, 163, 17, 0.15);
  color: var(--ws-secondary);
}

.icon-button.danger {
  border-color: rgba(255, 77, 77, 0.35);
  background: rgba(255, 77, 77, 0.08);
  color: #ffb4b4;
}

.comment-form {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.comment-form textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  resize: vertical;
}

.compact-notice {
  margin-top: 10px;
  padding: 12px;
}

.comment-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.comment-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
}

.comment-body {
  min-width: 0;
}

.comment-item p {
  margin: 6px 0 0;
  white-space: pre-wrap;
}

.comment-tools {
  align-content: start;
  justify-content: end;
}

@media (max-width: 640px) {
  .post-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .moderation-actions {
    justify-content: flex-start;
  }

  .comment-item {
    grid-template-columns: 1fr;
  }

  .comment-tools {
    justify-content: flex-start;
  }
}
</style>
