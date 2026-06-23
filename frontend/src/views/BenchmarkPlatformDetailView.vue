<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import PieChart from '../components/PieChart.vue';
import PlanCatalogPickers from '../components/PlanCatalogPickers.vue';
import { billingLabel, formatWon, parsePromoNotes, planMonthlyPrice } from '../utils/billing';
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
const threadTitle = ref('');
const threadBody = ref('');
const threadSaving = ref(false);
const platformCatalog = ref(null);

const platformId = computed(() => Number(route.params.id));
const axisKeys = ['availability', 'exclusivity', 'quality', 'price', 'accessibility'];
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

function formatScore(v) {
  return Number(v || 0).toFixed(2);
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
}

function applyReviewsBlock(block) {
  if (!page.value || !block) return;
  page.value.user_score = block.user_score;
  page.value.reviews = block.reviews;
  page.value.my_review = block.my_review;
}

async function loadCatalog() {
  try {
    platformCatalog.value = await apiRequest(`/api/subscriptions/platforms/${platformId.value}/catalog/`);
  } catch {
    platformCatalog.value = null;
  }
}

async function loadPage() {
  loading.value = true;
  error.value = '';
  try {
    page.value = await apiRequest(
      `/api/contents/benchmark/platforms/${platformId.value}/page/?use_llm=0`,
    );
    resetReviewForm();
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
    const data = await apiRequest(
      `/api/contents/benchmark/platforms/${platformId.value}/insight/`,
    );
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
    const data = await apiRequest(`/api/contents/benchmark/platforms/${platformId.value}/reviews/`, {
      method: 'POST',
      body: { score: reviewScore.value, body: reviewBody.value },
    });
    applyReviewsBlock(data);
    resetReviewForm();
    reviewSaved.value = true;
  } catch (err) {
    alert(err.message);
  } finally {
    reviewSaving.value = false;
  }
}

async function submitThread() {
  if (!session.isAuthenticated) {
    router.push('/login');
    return;
  }
  threadSaving.value = true;
  try {
    const post = await apiRequest('/api/community/posts/', {
      method: 'POST',
      body: {
        board: 'ott',
        platform_id: platformId.value,
        title: threadTitle.value,
        content: threadBody.value,
      },
    });
    threadTitle.value = '';
    threadBody.value = '';
    if (page.value) {
      page.value.community_threads = [post, ...(page.value.community_threads || [])].slice(0, 10);
    }
  } catch (err) {
    alert(err.message);
  } finally {
    threadSaving.value = false;
  }
}

onMounted(loadPage);
</script>

<template>
  <main class="platform-page">
    <p class="back-row">
      <RouterLink to="/benchmark">← 가성비 랭킹</RouterLink>
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

      <section class="panel compact">
        <h2>구독 플랜·번들·프로모션</h2>
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

      <section class="panel compact">
        <h2>유저 평가</h2>
        <div v-if="session.isAuthenticated" class="review-form" @click.stop @submit.prevent="submitReview">
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
          <button class="button primary" type="button" :disabled="reviewSaving" @click.prevent="submitReview">
            {{ reviewSaving ? '저장 중...' : '평가 저장' }}
          </button>
          <p v-if="reviewSaved" class="review-saved muted">평가가 저장되었습니다.</p>
        </div>
        <p v-else class="muted"><RouterLink to="/login">로그인</RouterLink> 후 평가할 수 있습니다.</p>

        <ul class="review-list">
          <li v-for="r in page.reviews" :key="r.id">
            <span class="review-stars">
              <span v-for="(on, i) in renderStars(r.score)" :key="i" :class="{ on }">★</span>
            </span>
            {{ r.author.nickname }}
            <p>{{ r.body || '(코멘트 없음)' }}</p>
          </li>
        </ul>
      </section>

      <section class="panel compact">
        <h2>플랫폼 토론</h2>
        <div v-if="session.isAuthenticated" class="review-form" @click.stop>
          <input v-model="threadTitle" type="text" placeholder="제목" />
          <textarea v-model="threadBody" rows="3" placeholder="토론 내용"></textarea>
          <button class="button" type="button" :disabled="threadSaving" @click.prevent="submitThread">글 작성</button>
        </div>
        <ul class="thread-list">
          <li v-for="post in page.community_threads" :key="post.id">
            <RouterLink :to="`/community/${post.id}`">{{ post.title }}</RouterLink>
            <span class="muted">{{ post.author.nickname }} · 댓글 {{ post.comment_count }}</span>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>

<style scoped>
.platform-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 20px 24px;
}

.back-row {
  margin-bottom: 10px;
}

/* Avoid global .hero (min-height 430px) — use platform-hero only */
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

.plan-list li,
.review-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--ws-border);
  display: grid;
  gap: 4px;
}

.review-form {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.review-form input,
.review-form textarea {
  padding: 10px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: inherit;
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

.review-stars {
  display: inline-flex;
  gap: 1px;
  margin-right: 6px;
}

.review-stars span {
  color: var(--ws-border);
  font-size: 14px;
}

.review-stars span.on {
  color: #f59e0b;
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
