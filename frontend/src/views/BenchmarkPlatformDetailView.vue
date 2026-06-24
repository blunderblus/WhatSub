<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import {
  addBenchmarkReviewComment,
  deleteBenchmarkPlatformReview,
  deleteBenchmarkReviewComment,
  fetchBenchmarkPlatformInsight,
  fetchBenchmarkPlatformPage,
  fetchPlatformCatalog,
  reactBenchmarkPlatformReview,
  saveBenchmarkPlatformReview,
} from '../api/benchmark';
import PieChart from '../components/PieChart.vue';
import PlanCatalogPickers from '../components/PlanCatalogPickers.vue';
import { billingLabel, formatWon, parsePromoNotes } from '../utils/billing';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();

const loading = ref(true);
const insightLoading = ref(false);
const error = ref('');
const page = ref(null);
const reviewScore = ref(0);
const reviewBody = ref('');
const reviewSaving = ref(false);
const reviewSaved = ref(false);
const reviewEditing = ref(false);
const scoreTab = ref('all');
const platformCatalog = ref(null);
const expandedComments = ref(new Set());
const commentDrafts = ref({});
const commentSaving = ref({});
const reactionSaving = ref({});

const platformId = computed(() => Number(route.params.id));
const axisKeys = ['availability', 'exclusivity', 'quality', 'price', 'accessibility'];
const scoreBucketOrder = ['very_positive', 'positive', 'mixed', 'negative', 'very_negative'];
const scoreBucketLabels = {
  very_positive: '매우 긍정적',
  positive: '긍정적',
  mixed: '복합적',
  negative: '부정적',
  very_negative: '매우 부정적',
};

const genreSegments = computed(() =>
  (page.value?.genres || []).slice(0, 8).map((g) => ({
    label: g.genre_name,
    value: g.title_count,
  })),
);

const heroDescription = computed(() => {
  if (!page.value) return '';
  if (page.value.description) return page.value.description;
  return `${page.value.title_count}편 분석 · 신뢰도 ${page.value.confidence_level}`;
});

const hasMyReview = computed(() => Boolean(page.value?.my_review));
const activeScoreSummary = computed(() => page.value?.score_summary?.[scoreTab.value] || null);
const communityBoard = computed(() => page.value?.community_board || null);
const displayReviews = computed(() => {
  const reviews = page.value?.reviews || [];
  if (!hasMyReview.value) return reviews;
  return reviews.filter((r) => !r.is_owner);
});

function formatScore(v) {
  return Number(v || 0).toFixed(2);
}

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function bucketPercent(dist, key) {
  const total = scoreBucketOrder.reduce((sum, k) => sum + (dist?.[k] || 0), 0);
  if (!total) return 0;
  return Math.round(((dist?.[key] || 0) / total) * 100);
}

function setReviewScore(score) {
  reviewScore.value = score;
  reviewSaved.value = false;
}

function renderStars(score) {
  return [1, 2, 3, 4, 5].map((n) => n <= score);
}

function resetReviewForm() {
  reviewScore.value = 0;
  reviewBody.value = '';
  reviewSaved.value = false;
  reviewEditing.value = false;
}

function prefillMyReview() {
  const mine = page.value?.my_review;
  if (!mine) {
    resetReviewForm();
    return;
  }
  reviewScore.value = mine.score;
  reviewBody.value = mine.body || '';
  reviewEditing.value = false;
}

function applyReviewsBlock(block) {
  if (!page.value || !block) return;
  page.value.user_score = block.user_score;
  page.value.score_summary = block.score_summary;
  page.value.reviews = block.reviews;
  page.value.my_review = block.my_review;
  prefillMyReview();
}

function startEditReview() {
  prefillMyReview();
  reviewEditing.value = true;
  reviewSaved.value = false;
}

function cancelEditReview() {
  prefillMyReview();
  reviewEditing.value = false;
}

function toggleComments(reviewId) {
  const next = new Set(expandedComments.value);
  if (next.has(reviewId)) next.delete(reviewId);
  else next.add(reviewId);
  expandedComments.value = next;
}

function isCommentsOpen(reviewId) {
  return expandedComments.value.has(reviewId);
}

async function loadCatalog() {
  try {
    platformCatalog.value = await fetchPlatformCatalog(platformId.value);
  } catch {
    platformCatalog.value = null;
  }
}

async function loadPage() {
  loading.value = true;
  error.value = '';
  try {
    page.value = await fetchBenchmarkPlatformPage(platformId.value, { useLlm: false });
    prefillMyReview();
    loadInsight();
    loadCatalog();
  } catch (err) {
    page.value = null;
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function loadInsight() {
  if (!page.value || insightLoading.value) return;
  insightLoading.value = true;
  try {
    const data = await fetchBenchmarkPlatformInsight(platformId.value);
    if (page.value && data.platform_id === page.value.platform_id) {
      page.value.llm_insight = data.llm_insight;
      page.value.llm_insight_month = data.llm_insight_month;
    }
  } catch {
    /* insight is optional */
  } finally {
    insightLoading.value = false;
  }
}

async function submitReview() {
  if (!session.isAuthenticated) {
    router.push('/login');
    return;
  }
  if (reviewScore.value < 1) {
    alert('별점을 선택해주세요.');
    return;
  }
  reviewSaving.value = true;
  reviewSaved.value = false;
  try {
    const data = await saveBenchmarkPlatformReview(platformId.value, {
      score: reviewScore.value,
      body: reviewBody.value,
    });
    applyReviewsBlock(data);
    reviewEditing.value = false;
    reviewSaved.value = true;
  } catch (err) {
    alert(err.message);
  } finally {
    reviewSaving.value = false;
  }
}

async function deleteMyReview() {
  if (!hasMyReview.value) return;
  if (!window.confirm('내 평가를 삭제할까요?')) return;
  reviewSaving.value = true;
  try {
    const data = await deleteBenchmarkPlatformReview(platformId.value);
    applyReviewsBlock(data);
    resetReviewForm();
  } catch (err) {
    alert(err.message);
  } finally {
    reviewSaving.value = false;
  }
}

async function toggleReaction(review, reaction) {
  if (!session.isAuthenticated) {
    router.push('/login');
    return;
  }
  if (review.is_owner) return;
  const key = review.id;
  if (reactionSaving.value[key]) return;
  reactionSaving.value = { ...reactionSaving.value, [key]: true };
  try {
    const next = review.reactions?.my_reaction === reaction ? null : reaction;
    const data = await reactBenchmarkPlatformReview(platformId.value, review.id, next);
    applyReviewsBlock(data);
  } catch (err) {
    alert(err.message);
  } finally {
    reactionSaving.value = { ...reactionSaving.value, [key]: false };
  }
}

async function submitComment(review) {
  if (!session.isAuthenticated) {
    router.push('/login');
    return;
  }
  const draft = (commentDrafts.value[review.id] || '').trim();
  if (!draft) return;
  commentSaving.value = { ...commentSaving.value, [review.id]: true };
  try {
    const data = await addBenchmarkReviewComment(platformId.value, review.id, draft);
    if (data.review) {
      const reviews = (page.value?.reviews || []).map((item) => (item.id === data.review.id ? data.review : item));
      page.value.reviews = reviews;
      if (page.value.my_review?.id === data.review.id) {
        page.value.my_review = data.review;
      }
    }
    commentDrafts.value = { ...commentDrafts.value, [review.id]: '' };
    expandedComments.value = new Set([...expandedComments.value, review.id]);
  } catch (err) {
    alert(err.message);
  } finally {
    commentSaving.value = { ...commentSaving.value, [review.id]: false };
  }
}

async function removeComment(review, comment) {
  if (!window.confirm('댓글을 삭제할까요?')) return;
  try {
    const data = await deleteBenchmarkReviewComment(platformId.value, comment.id);
    if (data.review) {
      const reviews = (page.value?.reviews || []).map((item) => (item.id === data.review.id ? data.review : item));
      page.value.reviews = reviews;
      if (page.value.my_review?.id === data.review.id) {
        page.value.my_review = data.review;
      }
    }
  } catch (err) {
    alert(err.message);
  }
}

watch(platformId, loadPage);
onMounted(loadPage);
</script>

<template>
  <main class="platform-page">
    <p class="back-row">
      <RouterLink to="/benchmark">← OTT순위</RouterLink>
    </p>

    <p v-if="error" class="notice">{{ error }}</p>
    <div v-else-if="loading" class="loader">플랫폼 정보를 불러오는 중입니다.</div>

    <template v-else-if="page">
      <section class="platform-hero panel">
        <div class="hero-head">
          <img v-if="page.icon_url" :src="page.icon_url" :alt="page.name" class="hero-icon" />
          <div class="hero-copy">
            <p class="eyebrow">Benchmark · {{ page.snapshot_date }}</p>
            <h1>{{ page.name }}</h1>
            <p class="muted">{{ heroDescription }}</p>
          </div>
        </div>

        <div class="hero-stats">
          <div><span>Value Score</span><strong>{{ formatScore(page.value_score) }}</strong></div>
          <div><span>유저 평점</span><strong>{{ page.user_score.average || '-' }} <small>({{ page.user_score.count }}명)</small></strong></div>
          <div><span>콘텐츠</span><strong>{{ page.title_count }}편</strong></div>
        </div>

        <div class="hero-actions">
          <RouterLink class="button primary" :to="page.content_links.movies">영화 보기</RouterLink>
          <RouterLink class="button secondary" :to="page.content_links.shows">시리즈 보기</RouterLink>
          <a v-if="page.website_url" class="button" :href="page.website_url" target="_blank" rel="noopener">공식 사이트</a>
        </div>
      </section>

      <div class="grid-2">
        <section class="panel compact">
          <h2>5축 벤치마크</h2>
          <div v-for="key in axisKeys" :key="key" class="axis-row">
            <span>{{ page.axis_labels[key] }}</span>
            <div class="bar"><span :style="{ width: `${Math.round((page.scores[key] || 0) * 100)}%` }"></span></div>
            <span>{{ formatScore(page.scores[key]) }}</span>
          </div>
        </section>

        <section class="panel compact">
          <h2>장르 분포</h2>
          <PieChart v-if="genreSegments.length" :segments="genreSegments" :size="180" />
          <p v-else class="muted">장르 데이터 없음</p>
        </section>
      </div>

      <section v-if="page.llm_insight || insightLoading" class="panel compact insight">
        <h2>AI 분석 <small class="muted">({{ page.llm_insight_month || '로딩 중' }})</small></h2>
        <p v-if="insightLoading && !page.llm_insight" class="muted">AI 분석을 불러오는 중입니다.</p>
        <template v-else-if="page.llm_insight">
          <p>{{ page.llm_insight.summary }}</p>
          <ul v-if="page.llm_insight.strengths?.length">
            <li v-for="(s, i) in page.llm_insight.strengths" :key="`s-${i}`">강점: {{ s }}</li>
          </ul>
          <ul v-if="page.llm_insight.weaknesses?.length">
            <li v-for="(w, i) in page.llm_insight.weaknesses" :key="`w-${i}`">약점: {{ w }}</li>
          </ul>
          <p v-if="page.llm_insight.best_for" class="muted">추천 대상: {{ page.llm_insight.best_for }}</p>
          <p v-if="page.llm_insight.plan_tip" class="muted">플랜 팁: {{ page.llm_insight.plan_tip }}</p>
        </template>
      </section>

      <section class="panel compact pricing-section">
        <div class="section-head">
          <h2>구독 플랜·번들·프로모션</h2>
          <RouterLink v-if="page.calculator_url" class="button secondary calc-link" :to="page.calculator_url">
            구독 계산기로 이동
          </RouterLink>
        </div>
        <PlanCatalogPickers
          v-if="platformCatalog"
          :catalog="platformCatalog"
          :platform-name="page.name"
          readonly
        />
        <div v-else-if="page.plans?.length" class="plan-section-fallback">
          <ul class="plan-list">
            <li v-for="plan in page.plans" :key="plan.id">
              <strong>{{ plan.plan_name }}</strong>
              <span>{{ formatWon(plan.price) }}원 · {{ billingLabel(plan.billing_period) }}</span>
              <span class="muted">{{ plan.max_quality }} · 동시 {{ plan.max_streams }} · {{ plan.has_ads ? '광고 있음' : '광고 없음' }}</span>
              <ul v-if="parsePromoNotes(plan.notes).length" class="promo-list">
                <li v-for="(promo, i) in parsePromoNotes(plan.notes)" :key="i">{{ promo }}</li>
              </ul>
            </li>
          </ul>
        </div>
        <div v-else class="muted">등록된 플랜 정보가 없습니다.</div>
      </section>

      <section v-if="page.exclusive_highlights?.length" class="panel compact">
        <h2>주요 독점작</h2>
        <div class="title-strip">
          <RouterLink v-for="t in page.exclusive_highlights" :key="`${t.tmdb_id}-${t.media_type}`" class="title-card" :to="t.detail_path">
            <img v-if="t.poster_url" :src="t.poster_url" :alt="t.title" loading="lazy" />
            <div v-else class="fallback">{{ t.title }}</div>
            <strong>{{ t.title }}</strong>
          </RouterLink>
        </div>
      </section>

      <section class="panel compact reviews-section">
        <h2>유저 평가</h2>

        <div class="reviews-wide">
          <div v-if="page.score_summary" class="steam-score">
            <div class="score-tabs" role="tablist">
              <button type="button" :class="{ active: scoreTab === 'recent' }" @click="scoreTab = 'recent'">최근 평가</button>
              <button type="button" :class="{ active: scoreTab === 'all' }" @click="scoreTab = 'all'">전체 평가</button>
            </div>
            <template v-if="activeScoreSummary">
              <p class="score-verdict" :data-key="activeScoreSummary.verdict?.key">
                {{ activeScoreSummary.verdict?.label || '평가 없음' }}
                <small v-if="activeScoreSummary.total">({{ activeScoreSummary.total }}명)</small>
              </p>
              <div class="score-bars">
                <div v-for="key in scoreBucketOrder" :key="key" class="score-bar-row">
                  <span class="score-bar-label">{{ scoreBucketLabels[key] }}</span>
                  <div class="score-bar-track">
                    <span :style="{ width: `${bucketPercent(activeScoreSummary.distribution, key)}%` }"></span>
                  </div>
                  <span class="score-bar-pct">{{ bucketPercent(activeScoreSummary.distribution, key) }}%</span>
                </div>
              </div>
            </template>
          </div>

          <div class="review-compose">
            <template v-if="session.isAuthenticated">
              <div v-if="hasMyReview && !reviewEditing" class="my-review-card">
                <div class="review-head">
                  <span class="review-stars">
                    <span v-for="(on, i) in renderStars(page.my_review.score)" :key="i" :class="{ on }">★</span>
                  </span>
                  <strong>내 평가</strong>
                </div>
                <p>{{ page.my_review.body || '(코멘트 없음)' }}</p>
                <div class="review-actions">
                  <button type="button" class="button" @click="startEditReview">수정</button>
                  <button type="button" class="button" :disabled="reviewSaving" @click="deleteMyReview">삭제</button>
                </div>
              </div>

              <div v-else class="review-form" @submit.prevent="submitReview">
                <p class="form-label">{{ hasMyReview ? '내 평가 수정' : '평가 작성' }}</p>
                <p v-if="!hasMyReview" class="muted form-hint">플랫폼당 1개의 평가만 작성할 수 있습니다.</p>
                <div class="star-input" role="group" aria-label="별점 선택">
                  <button
                    v-for="star in 5"
                    :key="star"
                    type="button"
                    class="star-btn"
                    :class="{ active: star <= reviewScore }"
                    :aria-label="`${star}점`"
                    @click.prevent="setReviewScore(star)"
                  >★</button>
                </div>
                <textarea v-model="reviewBody" rows="3" placeholder="이 플랫폼에 대한 의견을 남겨주세요."></textarea>
                <div class="review-actions">
                  <button class="button primary" type="button" :disabled="reviewSaving" @click.prevent="submitReview">
                    {{ reviewSaving ? '저장 중...' : '평가 저장' }}
                  </button>
                  <button v-if="hasMyReview" type="button" class="button" @click="cancelEditReview">취소</button>
                </div>
                <p v-if="reviewSaved" class="review-saved muted">평가가 저장되었습니다.</p>
              </div>
            </template>
            <p v-else class="muted"><RouterLink to="/login">로그인</RouterLink> 후 평가할 수 있습니다.</p>
          </div>
        </div>

        <h3 class="reviews-heading">주요 유저 평가</h3>
        <ul v-if="displayReviews.length" class="review-list">
          <li v-for="r in displayReviews" :key="r.id" class="review-item">
            <div class="review-head">
              <span class="review-stars">
                <span v-for="(on, i) in renderStars(r.score)" :key="i" :class="{ on }">★</span>
              </span>
              <strong>{{ r.author.nickname }}</strong>
              <span class="muted review-date">{{ formatDate(r.updated_at) }}</span>
            </div>
            <p class="review-body">{{ r.body || '(코멘트 없음)' }}</p>
            <div class="review-social">
              <button
                type="button"
                class="react-btn"
                :class="{ active: r.reactions?.my_reaction === 'like' }"
                :disabled="reactionSaving[r.id]"
                @click="toggleReaction(r, 'like')"
              >👍 {{ r.reactions?.like_count || 0 }}</button>
              <button
                type="button"
                class="react-btn"
                :class="{ active: r.reactions?.my_reaction === 'dislike' }"
                :disabled="reactionSaving[r.id]"
                @click="toggleReaction(r, 'dislike')"
              >👎 {{ r.reactions?.dislike_count || 0 }}</button>
              <button type="button" class="react-btn plain" @click="toggleComments(r.id)">
                댓글 {{ r.comment_count || 0 }}
              </button>
            </div>
            <div v-if="isCommentsOpen(r.id)" class="comment-block">
              <ul v-if="r.comments?.length" class="comment-list">
                <li v-for="c in r.comments" :key="c.id">
                  <strong>{{ c.author.nickname }}</strong>
                  <span class="muted">{{ formatDate(c.created_at) }}</span>
                  <p>{{ c.content }}</p>
                  <button v-if="c.is_owner" type="button" class="link-btn" @click="removeComment(r, c)">삭제</button>
                </li>
              </ul>
              <div v-if="session.isAuthenticated" class="comment-form">
                <textarea v-model="commentDrafts[r.id]" rows="2" placeholder="댓글을 입력하세요"></textarea>
                <button type="button" class="button" :disabled="commentSaving[r.id]" @click="submitComment(r)">
                  {{ commentSaving[r.id] ? '등록 중...' : '댓글 등록' }}
                </button>
              </div>
              <p v-else class="muted"><RouterLink to="/login">로그인</RouterLink> 후 댓글을 남길 수 있습니다.</p>
            </div>
          </li>
        </ul>
        <p v-else class="muted">아직 다른 유저의 평가가 없습니다.</p>
      </section>

      <section v-if="communityBoard" class="panel compact community-section">
        <div class="section-head">
          <h2>{{ communityBoard.platform_name }} 게시판</h2>
          <div class="community-links">
            <RouterLink class="button" :to="communityBoard.platform_board_url">게시판 바로가기</RouterLink>
            <RouterLink v-if="session.isAuthenticated" class="button primary" :to="communityBoard.platform_write_url">글쓰기</RouterLink>
          </div>
        </div>
        <p class="muted">OTT 게시판 · {{ communityBoard.platform_name }} 플레어</p>
        <ul v-if="communityBoard.threads?.length" class="thread-list">
          <li v-for="post in communityBoard.threads" :key="post.id" :class="{ 'is-notice': post.is_notice }">
            <RouterLink :to="`/community/${post.id}`">
              <span v-if="post.is_notice" class="flair notice">공지</span>
              <span v-else-if="post.platform_name" class="flair">{{ post.platform_name }}</span>
              <strong>{{ post.title }}</strong>
            </RouterLink>
            <span class="muted">{{ post.author.nickname }} · {{ formatDate(post.created_at) }}</span>
          </li>
        </ul>
        <p v-else class="muted">아직 게시글이 없습니다. 첫 글을 작성해보세요.</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.platform-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 20px 24px;
}

.back-row {
  margin-bottom: 10px;
}

.platform-hero {
  display: grid;
  gap: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
  min-height: 0;
  grid-template-columns: 1fr;
}

.hero-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.hero-icon {
  width: 52px;
  height: 52px;
  object-fit: contain;
  flex: none;
}

.hero-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.hero-copy h1 {
  font-size: 28px;
  line-height: 1.2;
}

.hero-copy .muted {
  margin: 0;
}

.hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

.hero-stats div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hero-stats strong {
  font-size: 20px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.panel.compact {
  padding: 14px 16px;
  margin-bottom: 14px;
}

.panel.compact h2 {
  margin: 0 0 12px;
  font-size: 17px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.section-head h2 {
  margin: 0;
}

.community-links {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.axis-row {
  display: grid;
  grid-template-columns: 72px 1fr 44px;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.bar {
  height: 6px;
  background: var(--ws-border);
  border-radius: 999px;
  overflow: hidden;
}

.bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--ws-primary), var(--ws-secondary));
}

.plan-list,
.review-list,
.thread-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.plan-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--ws-border);
  display: grid;
  gap: 4px;
}

.reviews-wide {
  display: grid;
  gap: 16px;
  margin-bottom: 18px;
}

@media (min-width: 900px) {
  .reviews-wide {
    grid-template-columns: minmax(280px, 340px) 1fr;
    align-items: start;
  }
}

.steam-score {
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.score-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.score-tabs button {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
}

.score-tabs button.active {
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
  border-color: var(--ws-primary);
}

.score-verdict {
  font-size: 18px;
  font-weight: 900;
  margin: 0 0 12px;
}

.score-verdict[data-key='very_positive'] { color: #66c0f4; }
.score-verdict[data-key='positive'] { color: #a4d007; }
.score-verdict[data-key='mixed'] { color: #b9a074; }
.score-verdict[data-key='negative'] { color: #c7996a; }
.score-verdict[data-key='very_negative'] { color: #a34c25; }

.score-bars {
  display: grid;
  gap: 8px;
}

.score-bar-row {
  display: grid;
  grid-template-columns: 72px 1fr 36px;
  gap: 8px;
  align-items: center;
  font-size: 12px;
}

.score-bar-track {
  height: 8px;
  background: var(--ws-border);
  border-radius: 4px;
  overflow: hidden;
}

.score-bar-track span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #66c0f4, #a4d007);
}

.score-bar-pct {
  text-align: right;
  color: var(--ws-muted);
}

.review-compose {
  min-width: 0;
}

.my-review-card,
.review-form {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.form-label {
  margin: 0;
  font-weight: 800;
}

.form-hint {
  margin: 0;
  font-size: 13px;
}

.review-form input,
.review-form textarea,
.comment-form textarea {
  padding: 10px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  color: inherit;
  width: 100%;
}

.star-input {
  display: flex;
  gap: 4px;
}

.star-btn {
  border: none;
  background: none;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  color: var(--ws-border);
  padding: 0 2px;
}

.star-btn.active {
  color: #f59e0b;
}

.reviews-heading {
  margin: 0 0 12px;
  font-size: 15px;
}

.review-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--ws-border);
}

.review-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.review-stars {
  display: inline-flex;
  gap: 1px;
}

.review-stars span {
  color: var(--ws-border);
  font-size: 14px;
}

.review-stars span.on {
  color: #f59e0b;
}

.review-date {
  font-size: 12px;
}

.review-body {
  margin: 8px 0;
}

.review-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.review-social {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.react-btn {
  border: 1px solid var(--ws-border);
  background: var(--ws-surface);
  border-radius: 999px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 13px;
}

.react-btn.active {
  border-color: var(--ws-primary);
  background: rgba(217, 221, 146, 0.12);
}

.react-btn.plain {
  background: transparent;
}

.comment-block {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: var(--ws-surface-2);
}

.comment-list {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: grid;
  gap: 8px;
}

.comment-list li p {
  margin: 4px 0 0;
}

.comment-form {
  display: grid;
  gap: 8px;
}

.link-btn {
  border: none;
  background: none;
  color: var(--ws-muted);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}

.thread-list li {
  display: grid;
  gap: 4px;
  padding: 8px 0;
  border-bottom: 1px solid var(--ws-border);
}

.thread-list a {
  display: flex;
  align-items: center;
  gap: 8px;
  color: inherit;
  text-decoration: none;
}

.thread-list a:hover strong {
  text-decoration: underline;
}

.thread-list li.is-notice {
  background: rgba(252, 163, 17, 0.06);
}

.flair {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  background: rgba(217, 221, 146, 0.2);
  color: var(--ws-primary);
  flex: none;
}

.flair.notice {
  background: rgba(252, 163, 17, 0.2);
  color: var(--ws-secondary);
}

.title-strip {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.title-card {
  flex: 0 0 100px;
  text-decoration: none;
  color: inherit;
}

.title-card img,
.fallback {
  width: 100px;
  height: 150px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid var(--ws-border);
}

.fallback {
  display: grid;
  place-items: center;
  font-size: 11px;
  padding: 6px;
  text-align: center;
}

.title-card strong {
  font-size: 12px;
  display: block;
  margin-top: 6px;
}

@media (max-width: 760px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }

  .hero-copy h1 {
    font-size: 24px;
  }
}
</style>
