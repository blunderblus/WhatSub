<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const movies = ref([]);
const shows = ref([]);
const dashboard = ref(null);

const previewItems = computed(() => [
  ...movies.value.slice(0, 3).map((item) => ({ ...item, type: 'movies' })),
  ...shows.value.slice(0, 3).map((item) => ({ ...item, type: 'shows' })),
]);

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
    <section class="home-hero" :class="{ 'guest-hero': !session.isAuthenticated }">
      <div class="hero-copy">
        <p class="eyebrow">WhatSub</p>
        <h1>구독 지출과 볼 수 있는 작품을 한 화면에서 확인하세요.</h1>
        <p class="muted">
          매달 빠져나가는 구독료, 다음 결제일, 영화와 시리즈의 OTT 제공처를 빠르게 확인합니다.
        </p>
        <div class="actions">
          <RouterLink v-if="session.isAuthenticated" class="button primary" to="/subscriptions">내 구독 보기</RouterLink>
          <RouterLink v-if="session.isAuthenticated" class="button" to="/subscriptions/new">구독 추가</RouterLink>
          <RouterLink v-if="!session.isAuthenticated" class="button primary" to="/signup">시작하기</RouterLink>
          <RouterLink v-if="!session.isAuthenticated" class="button dark" to="/login">로그인</RouterLink>
          <RouterLink class="button" to="/contents/search">작품 검색</RouterLink>
        </div>
      </div>

      <aside v-if="session.isAuthenticated" class="summary-panel">
        <div class="summary-head">
          <span>이번 달 예상 지출</span>
          <strong>{{ money(dashboard?.monthly_total) }}원</strong>
        </div>
        <div class="summary-metrics">
          <div><span>구독</span><strong>{{ dashboard?.subscription_count || 0 }}개</strong></div>
          <div><span>플랫폼</span><strong>{{ dashboard?.platform_count || 0 }}개</strong></div>
          <div><span>다음 결제</span><strong>{{ dashboard?.next_payment ? `D-${dashboard.next_payment.days}` : '-' }}</strong></div>
        </div>
      </aside>
    </section>

    <section class="home-content">
      <div class="section-head compact-head">
        <div>
          <h2>요즘 많이 찾는 작품</h2>
          <p class="muted">영화와 시리즈를 크게 넘겨 보면서 바로 찾아볼 수 있습니다.</p>
        </div>
        <div class="actions">
          <RouterLink class="button" to="/contents/movies">영화</RouterLink>
          <RouterLink class="button" to="/contents/shows">시리즈</RouterLink>
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

.home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 20px;
  align-items: stretch;
  padding: 24px;
  border: 1px solid #dce3e9;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 36px rgba(30, 41, 59, 0.07);
}

.guest-hero {
  grid-template-columns: 1fr;
}

.home-hero h1 {
  max-width: 680px;
  font-size: 32px;
}

.hero-copy {
  align-content: center;
}

.summary-panel {
  display: grid;
  gap: 14px;
  align-content: center;
  padding: 18px;
  border: 1px solid #dce3e9;
  border-radius: 8px;
  background: #f8fafb;
}

.summary-head span,
.summary-metrics span {
  color: #667586;
  font-size: 13px;
  font-weight: 800;
}

.summary-head strong {
  display: block;
  margin-top: 8px;
  color: #2f6f73;
  font-size: 32px;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-metrics div {
  min-height: 72px;
  padding: 12px;
  border-radius: 8px;
  background: #fff;
}

.summary-metrics strong {
  display: block;
  margin-top: 8px;
  font-size: 19px;
}

.home-content {
  overflow: hidden;
  padding: 18px 16px 16px;
  border: 1px solid #dce3e9;
  border-radius: 8px;
  background: #fff;
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
  border-radius: 8px;
  background: #101820;
  box-shadow: 0 14px 28px rgba(17, 24, 39, 0.18);
  scroll-snap-align: start;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.preview-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 36px rgba(17, 24, 39, 0.24);
}

.preview-card img,
.preview-empty {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  background: #dfe7ec;
  object-fit: cover;
}

.preview-empty {
  display: grid;
  place-items: center;
  padding: 18px;
  color: #44515e;
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
  background: linear-gradient(180deg, rgba(16, 24, 32, 0), rgba(16, 24, 32, 0.9));
  font-size: 18px;
  line-height: 1.3;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@media (max-width: 900px) {
  .home-hero {
    grid-template-columns: 1fr;
  }

  .preview-card {
    flex-basis: clamp(170px, 38vw, 230px);
  }
}

@media (max-width: 560px) {
  .home-hero {
    padding: 18px;
  }

  .home-hero h1 {
    font-size: 28px;
  }

  .summary-metrics {
    grid-template-columns: 1fr;
  }

  .preview-card {
    flex-basis: 64vw;
    min-height: 94vw;
  }
}
</style>
