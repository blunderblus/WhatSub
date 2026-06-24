<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import HomePlatformCarousel from '../components/HomePlatformCarousel.vue';
import { backendRoutes, backendUrl } from '../config/backend';
import { useHomeDiscovery } from '../composables/useHomeDiscovery';
import { useTimedCarousel } from '../composables/useTimedCarousel';
import { useSessionStore } from '../stores/session';
import { subscriptionsMonthlyTotal } from '../utils/billing';

const session = useSessionStore();
const router = useRouter();
const dashboard = ref(null);
const heroSlides = [
  {
    image: '/img/home-hero-1.jpg',
    eyebrow: 'WhatSub',
    title: '슬기로운 구독생활, 한 화면에서.',
    description: '매달 빠져나가는 OTT·멤버십 비용, 다음 결제일, 볼 수 있는 작품까지 한 번에 정리하세요.',
  },
  {
    image: '/img/home-hero-2.jpg',
    eyebrow: 'OTT Choice',
    title: '무엇을 볼지보다 먼저, 어디서 볼지.',
    description: '플랫폼별 인기 작품과 추천 랭킹을 함께 보고 내 구독 선택을 가볍게 만드세요.',
  },
];
const {
  activeIndex: activeHeroSlide,
  select: selectHeroSlide,
  start: startHeroCarousel,
  stop: stopHeroCarousel,
} = useTimedCarousel(heroSlides.length);
const {
  platformGroups,
  platformRecommendations,
  loading: discoveryLoading,
  error: discoveryError,
  hasPlatformGroups,
  loadHomeDiscovery,
} = useHomeDiscovery();
const monthlyTotal = computed(() => {
  const subscriptions = dashboard.value?.subscriptions;
  if (subscriptions?.length) return subscriptionsMonthlyTotal(subscriptions);
  return dashboard.value?.monthly_total || 0;
});

function money(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

async function loadDashboard() {
  if (!session.isAuthenticated) return;
  dashboard.value = await apiRequest('/api/accounts/dashboard/');
}

function openContentDetail(item) {
  router.push(`/contents/${item.kind}/${item.tmdb_id}`);
}

onMounted(async () => {
  startHeroCarousel();
  await Promise.all([loadHomeDiscovery(), loadDashboard()]);
});
</script>

<template>
  <main class="home">
    <section
      class="landing-hero panel"
      @mouseenter="stopHeroCarousel"
      @mouseleave="startHeroCarousel"
      @focusin="stopHeroCarousel"
      @focusout="startHeroCarousel"
    >
      <img
        v-for="(slide, index) in heroSlides"
        :key="slide.image"
        class="hero-bg"
        :class="{ active: index === activeHeroSlide }"
        :src="slide.image"
        alt=""
        aria-hidden="true"
      />
      <div class="hero-copy">
        <p class="eyebrow">{{ heroSlides[activeHeroSlide].eyebrow }}</p>
        <h1>{{ heroSlides[activeHeroSlide].title }}</h1>
        <p class="lead">{{ heroSlides[activeHeroSlide].description }}</p>
        <div class="actions">
          <a
            v-if="session.isAuthenticated"
            class="button primary"
            :href="backendUrl(backendRoutes.onboardingGmail)"
          >Gmail로 구독 찾기</a>
          <RouterLink v-if="session.isAuthenticated" class="button secondary" to="/subscriptions">내 대시보드</RouterLink>
          <RouterLink v-if="!session.isAuthenticated" class="button primary" to="/signup">시작하기</RouterLink>
        </div>
        <div class="hero-dots" aria-label="메인 이미지 선택">
          <button
            v-for="(slide, index) in heroSlides"
            :key="`${slide.image}-dot`"
            class="hero-dot"
            :class="{ active: index === activeHeroSlide }"
            type="button"
            :aria-label="`${index + 1}번째 메인 이미지`"
            @click="selectHeroSlide(index)"
          />
        </div>
        <div class="hero-points">
          <div>
            <span>결제일</span>
            <strong>놓치기 쉬운 갱신일을 먼저 확인</strong>
          </div>
          <div>
            <span>비용</span>
            <strong>월 구독 지출을 한 번에 계산</strong>
          </div>
          <div>
            <span>콘텐츠</span>
            <strong>볼 작품과 플랫폼을 함께 비교</strong>
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
      </div>

    </section>

    <section class="home-content panel">
      <div class="section-head compact-head">
        <div>
          <h2>요즘 많이 찾는 작품</h2>
        </div>
      </div>

      <p v-if="discoveryError" class="notice">{{ discoveryError }}</p>
      <div v-else-if="discoveryLoading" class="loader">작품 정보를 불러오는 중입니다.</div>
      <HomePlatformCarousel
        v-else-if="hasPlatformGroups"
        :groups="platformGroups"
        @open="openContentDetail"
      />
      <div v-else class="empty">표시할 콘텐츠가 없습니다.</div>
    </section>

    <section class="platform-recommend panel">
      <div class="section-head compact-head">
        <div>
          <h2>플랫폼 추천</h2>
        </div>
        <RouterLink class="button" to="/benchmark">자세히 보기</RouterLink>
      </div>

      <div v-if="platformRecommendations.length" class="recommend-grid">
        <RouterLink
          v-for="platform in platformRecommendations"
          :key="platform.platform_id"
          class="recommend-card"
          :to="`/benchmark/platforms/${platform.platform_id}`"
        >
          <div class="recommend-main">
            <img v-if="platform.icon_url" :src="platform.icon_url" :alt="platform.name" />
            <span v-else class="recommend-fallback">{{ platform.name?.charAt(0) }}</span>
            <div>
              <h3>{{ platform.name }}</h3>
              <p class="muted">{{ platform.reason }}</p>
            </div>
          </div>
          <strong>{{ platform.title_count }}편</strong>
        </RouterLink>
      </div>
      <div v-else-if="discoveryLoading" class="loader">추천 플랫폼을 불러오는 중입니다.</div>
      <div v-else class="empty">추천할 플랫폼 정보가 없습니다.</div>
    </section>
  </main>
</template>

<style scoped>
.home {
  display: grid;
  gap: 18px;
}

.landing-hero {
  position: relative;
  display: grid;
  min-height: 520px;
  padding: 34px;
  overflow: hidden;
  align-items: end;
  background: var(--ws-surface);
}

.landing-hero::after {
  position: absolute;
  inset: 0;
  content: '';
  background:
    linear-gradient(90deg, #02040a 0%, rgba(2, 4, 10, 0.96) 22%, rgba(2, 4, 10, 0.72) 48%, rgba(2, 4, 10, 0.2) 76%, rgba(2, 4, 10, 0) 100%),
    linear-gradient(0deg, rgba(2, 4, 10, 0.72), rgba(2, 4, 10, 0.08) 62%);
  pointer-events: none;
}

.hero-bg {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -8%;
  width: 120%;
  height: 100%;
  opacity: 0;
  object-fit: cover;
  object-position: center center;
  transition: opacity 700ms ease, transform 5200ms ease;
  transform: scale(1.02);
  transform-origin: center center;
}

.hero-bg.active {
  opacity: 1;
  transform: scale(1.06);
}

.hero-copy {
  position: relative;
  z-index: 1;
  max-width: 760px;
  display: grid;
  gap: 18px;
}

.landing-hero h1,
.landing-hero .eyebrow,
.landing-hero .lead {
  color: #fff;
}

.lead {
  max-width: 760px;
  font-size: 17px;
  font-weight: 750;
}

.hero-points {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 10px;
}

.hero-points div {
  min-height: 104px;
  padding: 16px;
  border: 1px solid rgba(var(--ws-primary-rgb), 0.34);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 16, 24, 0.72), rgba(var(--ws-primary-rgb), 0.1));
  backdrop-filter: blur(10px);
}

.hero-points div:nth-child(2) {
  border-color: rgba(var(--ws-secondary-rgb), 0.4);
  background: linear-gradient(145deg, rgba(12, 16, 24, 0.72), rgba(var(--ws-secondary-rgb), 0.13));
}

.hero-points span {
  display: block;
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 900;
}

.hero-points div:nth-child(2) span {
  color: var(--ws-secondary);
}

.hero-points strong {
  display: block;
  margin-top: 10px;
  color: #fff;
  font-size: 18px;
  line-height: 1.35;
}

.hero-dots {
  display: flex;
  gap: 8px;
}

.hero-dot {
  width: 28px;
  height: 8px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.42);
  cursor: pointer;
}

.hero-dot.active {
  background: #fff;
}

.summary-panel {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 18px;
  align-content: center;
  max-width: 720px;
  margin-top: 8px;
  padding: 24px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.38);
  border-radius: var(--ws-radius);
  background:
    linear-gradient(145deg, rgba(20, 33, 61, 0.94), rgba(var(--ws-secondary-rgb), 0.16)),
    var(--ws-surface-2);
  box-shadow: 0 18px 42px rgba(var(--ws-secondary-rgb), 0.16);
}

.summary-label {
  margin: 0;
  color: var(--ws-secondary);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.summary-amount {
  font-size: 36px;
  font-family: Comfortaa, "Asta Sans", sans-serif;
  color: #ffffff;
  line-height: 1;
}

.summary-amount small {
  font-size: 18px;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-metrics div {
  padding: 12px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
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
  color: var(--ws-primary);
}

.summary-metrics div:nth-child(2) strong {
  color: var(--ws-secondary);
}

.button.full {
  width: 100%;
}

.home-content {
  overflow: hidden;
  padding: 18px 16px 16px;
}

.compact-head {
  align-items: center;
}

.platform-recommend {
  padding: 18px;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.recommend-card {
  display: grid;
  min-height: 132px;
  padding: 14px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  transition: border-color 160ms ease, transform 160ms ease;
}

.recommend-card:hover {
  border-color: var(--ws-primary);
  transform: translateY(-2px);
}

.recommend-main {
  display: flex;
  gap: 10px;
}

.recommend-main img,
.recommend-fallback {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: #fff;
  color: #26323d;
  font-size: 16px;
  font-weight: 900;
  object-fit: contain;
}

.recommend-main h3 {
  font-size: 18px;
}

.recommend-main p {
  margin: 4px 0 0;
}

.recommend-card > strong {
  align-self: end;
  color: var(--ws-primary);
  font-family: Comfortaa, "Asta Sans", sans-serif;
}

@media (max-width: 560px) {
  .landing-hero {
    min-height: 640px;
    padding: 18px;
  }

  .hero-points,
  .summary-metrics {
    grid-template-columns: 1fr;
  }

  .recommend-grid {
    grid-template-columns: 1fr;
  }
}
</style>
