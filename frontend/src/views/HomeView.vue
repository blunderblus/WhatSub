<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';
import { subscriptionsMonthlyTotal } from '../utils/billing';

const BACKEND_URL = 'http://127.0.0.1:8000';
const session = useSessionStore();
const movies = ref([]);
const shows = ref([]);
const dashboard = ref(null);

const previewItems = computed(() => [
  ...movies.value.slice(0, 3).map((item) => ({ ...item, type: 'movies' })),
  ...shows.value.slice(0, 3).map((item) => ({ ...item, type: 'shows' })),
]);
const monthlyTotal = computed(() => {
  const subscriptions = dashboard.value?.subscriptions;
  if (subscriptions?.length) return subscriptionsMonthlyTotal(subscriptions);
  return dashboard.value?.monthly_total || 0;
});

function money(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

async function loadPreview() {
  const [movieData, showData] = await Promise.all([
    apiRequest('/api/contents/movie_list/?page=1'),
    apiRequest('/api/contents/show_list/?page=1'),
  ]);
  movies.value = movieData.results || [];
  shows.value = showData.results || [];
}

async function loadDashboard() {
  if (!session.isAuthenticated) return;
  dashboard.value = await apiRequest('/api/accounts/dashboard/');
}

onMounted(async () => {
  await Promise.all([loadPreview(), loadDashboard()]);
});
</script>

<template>
  <main class="home">
    <section class="landing-hero panel">
      <div class="hero-copy">
        <p class="eyebrow">WhatSub</p>
        <h1>슬기로운 구독생활,<br />한 화면에서.</h1>
        <p class="muted lead">
          매달 빠져나가는 OTT·멤버십 비용, 다음 결제일, 볼 수 있는 작품까지.
          Gmail 스캔으로 구독을 자동 등록하고 최적화해 보세요.
        </p>
        <div class="actions">
          <a
            v-if="session.isAuthenticated"
            class="button primary"
            :href="`${BACKEND_URL}/accounts/onboarding/gmail/`"
          >Gmail로 구독 찾기</a>
          <RouterLink v-if="session.isAuthenticated" class="button secondary" to="/subscriptions">내 대시보드</RouterLink>
          <RouterLink v-if="!session.isAuthenticated" class="button primary" to="/signup">시작하기</RouterLink>
          <RouterLink v-if="!session.isAuthenticated" class="button" to="/login">로그인</RouterLink>
          <RouterLink class="button" to="/contents/search">작품 검색</RouterLink>
          <RouterLink class="button" to="/benchmark">OTT 가성비 랭킹</RouterLink>
        </div>
        <div class="hero-stats">
          <div><span>자동 스캔</span><strong>Gmail</strong></div>
          <div><span>작품 탐색</span><strong>OTT</strong></div>
          <div><span>커뮤니티</span><strong>가성비</strong></div>
        </div>
      </div>

      <aside v-if="session.isAuthenticated && dashboard" class="summary-panel">
        <p class="summary-label">이번 달 예상 지출</p>
        <strong class="summary-amount">{{ money(monthlyTotal) }}<small>원</small></strong>
        <div class="summary-metrics">
          <div><span>구독</span><strong>{{ dashboard.subscription_count }}개</strong></div>
          <div><span>플랫폼</span><strong>{{ dashboard.platform_count }}개</strong></div>
          <div><span>다음 결제</span><strong>{{ dashboard.next_payment ? `D-${dashboard.next_payment.days}` : '-' }}</strong></div>
        </div>
        <RouterLink class="button primary full" to="/subscriptions">대시보드 열기</RouterLink>
      </aside>

      <aside v-else class="summary-panel demo-panel">
        <p class="summary-label">WhatSub 미리보기</p>
        <div class="demo-bars">
          <div style="--h:72%"><span>Netflix</span></div>
          <div style="--h:48%"><span>Wavve</span></div>
          <div style="--h:56%"><span>TVING</span></div>
        </div>
        <p class="muted demo-note">가입 후 Gmail 스캔으로 내 구독을 자동 등록할 수 있어요.</p>
      </aside>
    </section>

    <section class="home-content panel">
      <div class="section-head compact-head">
        <div>
          <h2>요즘 많이 찾는 작품</h2>
          <p class="muted">포스터에 마우스를 올리면 OTT 시청처 아이콘이 표시됩니다.</p>
        </div>
        <div class="actions">
          <RouterLink class="button" to="/contents/movies">영화</RouterLink>
          <RouterLink class="button" to="/contents/shows">시리즈</RouterLink>
          <RouterLink class="button" to="/community">커뮤니티</RouterLink>
        </div>
      </div>

      <div v-if="previewItems.length" class="preview-strip">
        <RouterLink
          v-for="item in previewItems"
          :key="`${item.type}-${item.tmdb_id}`"
          class="preview-card"
          :to="`/contents/${item.type}/${item.tmdb_id}`"
        >
          <img v-if="item.poster_url" :src="item.poster_url" :alt="item.title" loading="lazy" />
          <div v-else class="preview-empty">{{ item.title }}</div>
          <strong>{{ item.title }}</strong>
        </RouterLink>
      </div>
      <div v-else class="empty">작품 정보를 불러오는 중입니다.</div>
    </section>
  </main>
</template>

<style scoped>
.home {
  display: grid;
  gap: 18px;
}

.landing-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 24px;
  padding: 28px;
  overflow: hidden;
  background:
    radial-gradient(circle at 100% 0%, rgba(198, 243, 73, 0.1), transparent 40%),
    var(--ws-surface);
}

.lead {
  max-width: 520px;
  font-size: 16px;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 8px;
}

.hero-stats div {
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.hero-stats span {
  display: block;
  color: var(--ws-muted);
  font-size: 12px;
  font-weight: 800;
}

.hero-stats strong {
  display: block;
  margin-top: 6px;
  color: var(--ws-primary);
  font-family: Poppins, Pretendard, sans-serif;
}

.summary-panel {
  display: grid;
  gap: 14px;
  align-content: center;
  padding: 20px;
  border: 1px solid var(--ws-border);
  border-radius: var(--ws-radius);
  background: var(--ws-surface-2);
}

.summary-label {
  margin: 0;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 800;
}

.summary-amount {
  font-size: 36px;
  font-family: Poppins, Pretendard, sans-serif;
  color: var(--ws-primary);
  line-height: 1;
}

.summary-amount small {
  font-size: 18px;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-metrics div {
  padding: 10px;
  border-radius: 8px;
  background: var(--ws-surface);
  border: 1px solid var(--ws-border);
}

.summary-metrics span {
  display: block;
  color: var(--ws-muted);
  font-size: 11px;
  font-weight: 800;
}

.summary-metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 16px;
}

.button.full {
  width: 100%;
}

.demo-bars {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 120px;
}

.demo-bars div {
  flex: 1;
  height: var(--h);
  border-radius: 8px 8px 4px 4px;
  background: linear-gradient(180deg, var(--ws-primary), rgba(198, 243, 73, 0.2));
  display: grid;
  align-items: end;
  padding: 6px;
}

.demo-bars span {
  font-size: 10px;
  font-weight: 800;
  color: var(--ws-primary-fg);
}

.demo-note {
  margin: 0;
  font-size: 13px;
}

.home-content {
  overflow: hidden;
  padding: 18px 16px 16px;
}

.compact-head {
  align-items: center;
}

.preview-strip {
  display: flex;
  gap: 16px;
  margin-inline: -16px;
  padding: 4px 16px 8px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
}

.preview-card {
  position: relative;
  display: grid;
  align-items: end;
  flex: 0 0 clamp(180px, 20vw, 260px);
  min-height: clamp(270px, 30vw, 390px);
  overflow: hidden;
  border-radius: var(--ws-radius);
  background: #101820;
  box-shadow: var(--ws-shadow);
  scroll-snap-align: start;
  transition: transform 160ms ease, box-shadow 160ms ease;
  border: 1px solid var(--ws-border);
}

.preview-card:hover {
  transform: translateY(-4px);
  border-color: var(--ws-primary);
}

.preview-card img,
.preview-empty {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  background: var(--ws-surface-2);
  object-fit: cover;
}

.preview-empty {
  display: grid;
  place-items: center;
  padding: 18px;
  color: var(--ws-muted);
  text-align: center;
  font-size: 18px;
  font-weight: 800;
}

.preview-card strong {
  position: relative;
  z-index: 1;
  display: -webkit-box;
  overflow: hidden;
  padding: 44px 14px 14px;
  color: #fff;
  background: linear-gradient(180deg, rgba(16, 24, 32, 0), rgba(16, 24, 32, 0.92));
  font-size: 18px;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@media (max-width: 900px) {
  .landing-hero {
    grid-template-columns: 1fr;
  }

  .preview-card {
    flex-basis: clamp(170px, 38vw, 230px);
  }
}

@media (max-width: 560px) {
  .landing-hero {
    padding: 18px;
  }

  .hero-stats,
  .summary-metrics {
    grid-template-columns: 1fr;
  }

  .preview-card {
    flex-basis: 64vw;
    min-height: 94vw;
  }
}
</style>
