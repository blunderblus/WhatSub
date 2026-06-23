<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import {
  fetchBenchmarkLeaderboard,
  fetchBenchmarkPlatform,
  fetchPersonalBenchmark,
  fetchPlatformCatalog,
} from '../api/benchmark';
import PageHeader from '../components/PageHeader.vue';
import PieChart from '../components/PieChart.vue';
import SubscriptionCalculator from '../components/SubscriptionCalculator.vue';
import PlanCatalogPickers from '../components/PlanCatalogPickers.vue';
import { useBenchmarkAxisTooltips } from '../composables/useBenchmarkAxisTooltips';
import { formatWon } from '../utils/billing';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const session = useSessionStore();
const activeTab = ref(route.query.tab === 'personal' ? 'personal' : 'benchmark');
const loading = ref(false);
const error = ref('');
const leaderboard = ref(null);
const selectedId = ref(null);
const hoverId = ref(null);
const detail = ref(null);
const detailLoading = ref(false);
const personal = ref(null);
const personalLoading = ref(false);
const personalError = ref('');
const platformCatalog = ref(null);
const plansLoading = ref(false);
const calcItems = ref([]);

const platforms = computed(() => leaderboard.value?.platforms || []);
const axisLabels = computed(() => leaderboard.value?.axis_labels || {});
const axisKeys = ['availability', 'exclusivity', 'quality', 'price', 'accessibility'];

const monthlyBudget = computed(() => personal.value?.monthly_spend_cap ?? null);
const existingMonthly = computed(() => personal.value?.existing_monthly_total ?? 0);

const calcMonthlyTotal = computed(() =>
  calcItems.value.reduce((sum, item) => sum + Number(item.monthly_price || 0), 0),
);

const projectedMonthly = computed(() => existingMonthly.value + calcMonthlyTotal.value);

const budgetExceeded = computed(() =>
  monthlyBudget.value != null
  && monthlyBudget.value > 0
  && projectedMonthly.value > monthlyBudget.value,
);

const activeBenchmarkPlatformId = computed(() => hoverId.value ?? selectedId.value);

const activeBenchmarkPlatform = computed(() =>
  platforms.value.find((p) => p.platform_id === activeBenchmarkPlatformId.value) || null,
);

const selectedPlatform = computed(() => activeBenchmarkPlatform.value);

const shareSegments = computed(() =>
  platforms.value.map((p) => ({
    label: p.name,
    value: p.title_count,
  })),
);

const genreSegments = computed(() =>
  (detail.value?.genres || []).slice(0, 8).map((g) => ({
    label: g.genre_name,
    value: g.title_count,
  })),
);

const personalSelected = computed(() => {
  if (!personal.value?.platforms?.length) return null;
  const id = selectedId.value || personal.value.platforms[0].platform_id;
  return personal.value.platforms.find((p) => p.platform_id === id) || personal.value.platforms[0];
});

const { activeTooltip, axisTooltips, toggleTooltip } = useBenchmarkAxisTooltips();

function formatScore(value) {
  return Number(value || 0).toFixed(2);
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function confidenceLabel(level) {
  if (level === 'high') return '높음';
  if (level === 'medium') return '보통';
  return '낮음';
}

function platformBudgetWarning(platform) {
  if (!monthlyBudget.value || monthlyBudget.value <= 0 || !platform?.min_monthly_plan) return false;
  return existingMonthly.value + calcMonthlyTotal.value + platform.min_monthly_plan > monthlyBudget.value;
}

function addCalcItem(item) {
  calcItems.value = [...calcItems.value, item];
}

function onCalcDropItem(item) {
  if (item?.uid) addCalcItem(item);
}

async function loadPlatformCatalog(platformId) {
  if (!platformId) {
    platformCatalog.value = null;
    return;
  }
  plansLoading.value = true;
  try {
    platformCatalog.value = await fetchPlatformCatalog(platformId);
  } catch {
    platformCatalog.value = null;
  } finally {
    plansLoading.value = false;
  }
}

async function loadLeaderboard() {
  loading.value = true;
  error.value = '';
  try {
    leaderboard.value = await fetchBenchmarkLeaderboard();
    if (!selectedId.value && leaderboard.value.platforms?.length) {
      selectedId.value = leaderboard.value.platforms[0].platform_id;
    }
  } catch (err) {
    leaderboard.value = null;
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function loadDetail(platformId) {
  if (!platformId) {
    detail.value = null;
    return;
  }
  detailLoading.value = true;
  try {
    detail.value = await fetchBenchmarkPlatform(platformId);
  } catch {
    detail.value = null;
  } finally {
    detailLoading.value = false;
  }
}

async function loadPersonal() {
  if (!session.isAuthenticated) return;
  personalLoading.value = true;
  personalError.value = '';
  try {
    personal.value = await fetchPersonalBenchmark();
    if (personal.value?.platforms?.length) {
      const exists = personal.value.platforms.some((p) => p.platform_id === selectedId.value);
      if (!exists) {
        selectedId.value = personal.value.platforms[0].platform_id;
      }
      await loadPlatformCatalog(selectedId.value);
    }
  } catch (err) {
    personal.value = null;
    personalError.value = err.message;
  } finally {
    personalLoading.value = false;
  }
}

function selectPlatform(platformId) {
  selectedId.value = platformId;
  hoverId.value = null;
  if (activeTab.value === 'personal') {
    loadPlatformCatalog(platformId);
  }
}

function onBenchmarkHover(platformId) {
  hoverId.value = platformId;
}

function onBenchmarkLeave() {
  hoverId.value = null;
}

watch(activeBenchmarkPlatformId, (id) => {
  if (activeTab.value === 'benchmark' && id) {
    loadDetail(id);
  }
});

watch(selectedId, (id) => {
  if (activeTab.value === 'benchmark' && id && !hoverId.value) {
    loadDetail(id);
  }
});

watch(() => route.query.tab, (tab) => {
  if (tab === 'personal') activeTab.value = 'personal';
});

watch(activeTab, (tab) => {
  if (tab === 'personal' && session.isAuthenticated) {
    if (!personal.value) loadPersonal();
    else if (selectedId.value) loadPlatformCatalog(selectedId.value);
  }
});

onMounted(async () => {
  await loadLeaderboard();
  if (session.isAuthenticated && activeTab.value === 'personal') {
    await loadPersonal();
  }
});
</script>

<template>
  <main class="benchmark-page">
    <PageHeader
      eyebrow="Benchmark"
      title="OTT 가성비 & 맞춤 추천"
      description="글로벌 벤치마크 리더보드와, 취향 기반 Personal Score를 함께 확인할 수 있습니다."
    />

    <nav class="tab-nav" aria-label="벤치마크 탭">
      <button type="button" class="tab-btn" :class="{ active: activeTab === 'benchmark' }" @click="activeTab = 'benchmark'">
        가성비 랭킹
      </button>
      <button type="button" class="tab-btn" :class="{ active: activeTab === 'personal' }" @click="activeTab = 'personal'">
        나에게 맞는 OTT
      </button>
    </nav>

    <!-- Benchmark tab -->
    <template v-if="activeTab === 'benchmark'">
      <p v-if="error" class="notice">{{ error }}</p>
      <div v-else-if="loading" class="loader">벤치마크 데이터를 불러오는 중입니다.</div>

      <template v-else-if="leaderboard">
        <section class="meta-bar panel">
          <span>스냅샷: {{ leaderboard.snapshot_date }}</span>
          <span>분석 작품 {{ leaderboard.global_title_count }}편</span>
          <span>플랫폼 {{ platforms.length }}개</span>
        </section>

        <section class="panel charts-row">
          <div class="chart-block">
            <h3>플랫폼 콘텐츠 점유율</h3>
            <PieChart :segments="shareSegments" :size="180" />
          </div>
          <div class="chart-block">
            <h3>{{ activeBenchmarkPlatform?.name || '플랫폼' }} 장르 분포</h3>
            <p v-if="detailLoading" class="muted">불러오는 중...</p>
            <PieChart v-else-if="genreSegments.length" :segments="genreSegments" :size="180" />
            <p v-else class="muted">플랫폼을 선택하면 장르 파이차트가 표시됩니다.</p>
          </div>
        </section>

        <div class="benchmark-layout">
          <section class="panel leaderboard-panel">
            <h2>종합 랭킹</h2>
            <ol class="rank-list">
              <li
                v-for="(platform, index) in platforms"
                :key="platform.platform_id"
                class="rank-item"
                :class="{ active: activeBenchmarkPlatformId === platform.platform_id }"
                @mouseenter="onBenchmarkHover(platform.platform_id)"
                @mouseleave="onBenchmarkLeave"
              >
                <RouterLink
                  class="rank-button"
                  :to="`/benchmark/platforms/${platform.platform_id}`"
                  @mouseenter="onBenchmarkHover(platform.platform_id)"
                  @focus="onBenchmarkHover(platform.platform_id)"
                >
                  <span class="rank-num">{{ index + 1 }}</span>
                  <img v-if="platform.icon_url" :src="platform.icon_url" :alt="platform.name" class="platform-icon" />
                  <span v-else class="platform-icon fallback">{{ platform.name.charAt(0) }}</span>
                  <span class="rank-info">
                    <strong>{{ platform.name }}</strong>
                    <span class="muted">{{ platform.title_count }}편 · 신뢰도 {{ confidenceLabel(platform.confidence_level) }}</span>
                  </span>
                  <span class="rank-score">
                    <strong>{{ formatScore(platform.value_score) }}</strong>
                    <span class="score-bar" aria-hidden="true">
                      <span :style="{ width: formatPercent(platform.value_score) }"></span>
                    </span>
                  </span>
                </RouterLink>
              </li>
            </ol>
          </section>

          <section v-if="activeBenchmarkPlatform" class="panel detail-panel">
            <div class="detail-head">
              <img v-if="activeBenchmarkPlatform.icon_url" :src="activeBenchmarkPlatform.icon_url" :alt="activeBenchmarkPlatform.name" class="platform-icon lg" />
              <div>
                <h2>{{ activeBenchmarkPlatform.name }}</h2>
                <p class="muted">Value Score {{ formatScore(activeBenchmarkPlatform.value_score) }} · {{ activeBenchmarkPlatform.title_count }}편</p>
              </div>
              <span class="confidence-badge" :data-level="activeBenchmarkPlatform.confidence_level">
                신뢰도 {{ confidenceLabel(activeBenchmarkPlatform.confidence_level) }}
              </span>
            </div>

            <div class="axis-grid">
              <div v-for="key in axisKeys" :key="key" class="axis-row">
                <span class="axis-label">
                  {{ axisLabels[key] || key }}
                  <span
                    class="info-icon"
                    tabindex="0"
                    :class="{ active: activeTooltip === key }"
                    @click.stop="toggleTooltip(key)"
                  >
                    ⓘ
                    <span class="tooltip">{{ axisTooltips[key] }}</span>
                  </span>
                </span>
                <div class="axis-bar">
                  <span :style="{ width: formatPercent(activeBenchmarkPlatform.scores[key]) }"></span>
                </div>
                <span class="axis-value">{{ formatScore(activeBenchmarkPlatform.scores[key]) }}</span>
              </div>
            </div>
          </section>
        </div>
      </template>
    </template>

    <!-- Personal tab -->
    <template v-else>
      <div v-if="!session.isAuthenticated" class="panel auth-prompt">
        <p>Personal Score는 로그인 후 이용할 수 있습니다.</p>
        <p class="muted">작품 좋아요/싫어요, 온보딩 취향 설정이 점수에 반영됩니다.</p>
        <RouterLink class="button primary" to="/login">로그인</RouterLink>
      </div>

      <template v-else>
        <div class="pref-actions">
          <RouterLink class="button secondary" to="/onboarding/preferences">취향 설정하기</RouterLink>
          <button class="button" type="button" :disabled="personalLoading" @click="loadPersonal">새로고침</button>
        </div>

        <p v-if="personalError" class="notice">{{ personalError }}</p>
        <div v-else-if="personalLoading" class="loader">맞춤 점수를 계산하는 중입니다.</div>

        <template v-else-if="personal">
          <section v-if="personal.taste_summary" class="panel taste-summary">
            <h3>취향 요약</h3>
            <p>{{ personal.taste_summary }}</p>
            <p v-if="personal.taste_meta" class="muted small">
              좋아요 {{ personal.taste_meta.likes }} · 싫어요 {{ personal.taste_meta.dislikes }}
              <span v-if="personal.taste_meta.llm_available_today">
                · AI 취향 분석 {{ personal.taste_meta.llm_runs_remaining }}/{{ personal.taste_meta.llm_limit }}회 남음
              </span>
              <span v-else-if="personal.taste_meta.llm_ran_today">
                · 오늘 AI 분석 {{ personal.taste_meta.llm_runs_today }}/{{ personal.taste_meta.llm_limit }}회 사용
              </span>
            </p>
          </section>

          <p v-if="monthlyBudget" class="budget-hint muted small">
            월 OTT 예산: {{ formatWon(monthlyBudget) }}원
            <span v-if="existingMonthly"> · 현재 구독 {{ formatWon(existingMonthly) }}원/월</span>
          </p>
          <p v-if="budgetExceeded" class="budget-banner-warn">
            계산기 합계가 월 예산을 초과합니다. (예상 {{ formatWon(projectedMonthly) }}원/월)
          </p>

          <p v-if="personal.detail" class="notice">{{ personal.detail }}</p>

          <div v-if="personal.platforms?.length" class="benchmark-layout">
            <section class="panel leaderboard-panel">
              <h2>맞춤 추천 순위</h2>
              <ol class="rank-list">
                <li
                  v-for="(platform, index) in personal.platforms"
                  :key="platform.platform_id"
                  class="rank-item"
                  :class="{ active: selectedId === platform.platform_id }"
                >
                  <button type="button" class="rank-button" @click="selectPlatform(platform.platform_id)">
                    <span class="rank-num">{{ index + 1 }}</span>
                    <img v-if="platform.icon_url" :src="platform.icon_url" :alt="platform.name" class="platform-icon" />
                    <span v-else class="platform-icon fallback">{{ platform.name.charAt(0) }}</span>
                    <span class="rank-info">
                      <strong>{{ platform.name }}</strong>
                      <span class="muted">장르 {{ formatScore(platform.genre_benefit_score) }} · 독점 {{ formatScore(platform.exclusivity_affinity_score) }}</span>
                      <span v-if="platformBudgetWarning(platform)" class="budget-chip">예산 초과 가능</span>
                    </span>
                    <span class="rank-score">
                      <strong>{{ formatScore(platform.personal_score) }}</strong>
                    </span>
                  </button>
                </li>
              </ol>
            </section>

            <section v-if="personalSelected" class="panel detail-panel report-panel">
              <h2>{{ personalSelected.name }} 추천 리포트</h2>
              <p class="muted">Personal Score {{ formatScore(personalSelected.personal_score) }}</p>

              <div class="score-pills">
                <span>장르 편익 {{ formatScore(personalSelected.genre_benefit_score) }}</span>
                <span>독점 affinity {{ formatScore(personalSelected.exclusivity_affinity_score) }}</span>
                <span v-if="personalSelected.benchmark_value_score != null">벤치마크 {{ formatScore(personalSelected.benchmark_value_score) }}</span>
              </div>

              <h3>이 플랫폼을 추천하는 이유</h3>
              <ul class="reason-list">
                <li v-for="(reason, i) in personalSelected.reasons" :key="i">{{ reason }}</li>
              </ul>

              <h3 v-if="personalSelected.top_genres?.length">장르 매칭</h3>
              <ul v-if="personalSelected.top_genres?.length" class="genre-match-list">
                <li v-for="g in personalSelected.top_genres" :key="g.genre_id">
                  {{ g.genre_name }} · {{ g.title_count }}편 (매칭 {{ g.match_score }})
                </li>
              </ul>

              <div v-if="personalSelected.liked_titles?.length" class="title-section">
                <h3>내가 좋아요한 작품</h3>
                <p class="muted small">이 플랫폼에서 시청 가능한 좋아요 작품입니다.</p>
                <div class="title-strip">
                  <RouterLink
                    v-for="title in personalSelected.liked_titles"
                    :key="`liked-${title.tmdb_id}-${title.media_type}`"
                    class="title-card"
                    :to="title.detail_path"
                  >
                    <img v-if="title.poster_url" :src="title.poster_url" :alt="title.title" loading="lazy" />
                    <div v-else class="title-poster-fallback">{{ title.title }}</div>
                    <strong>{{ title.title }}</strong>
                    <span v-if="title.vote_average" class="title-meta">★ {{ Number(title.vote_average).toFixed(1) }}</span>
                  </RouterLink>
                </div>
              </div>
              <p v-else class="muted small">이 플랫폼에서 시청 가능한 좋아요 작품이 아직 없습니다.</p>

              <div v-if="personalSelected.exclusive_highlights?.length" class="title-section">
                <h3>주요 독점작</h3>
                <p class="muted small">캐시 기준 이 플랫폼에서만 제공되는 인기 작품입니다.</p>
                <div class="title-strip">
                  <RouterLink
                    v-for="title in personalSelected.exclusive_highlights"
                    :key="`ex-${title.tmdb_id}-${title.media_type}`"
                    class="title-card"
                    :to="title.detail_path"
                  >
                    <span class="badge exclusive">독점</span>
                    <img v-if="title.poster_url" :src="title.poster_url" :alt="title.title" loading="lazy" />
                    <div v-else class="title-poster-fallback">{{ title.title }}</div>
                    <strong>{{ title.title }}</strong>
                    <span v-if="title.vote_average" class="title-meta">★ {{ Number(title.vote_average).toFixed(1) }}</span>
                  </RouterLink>
                </div>
              </div>

              <div class="plan-section">
                <h3>이용 가능한 요금·번들·프로모션</h3>
                <p class="muted small">클릭하거나 구독 계산기로 드래그해서 예상 월 비용을 확인하세요.</p>
                <PlanCatalogPickers
                  :catalog="platformCatalog || {}"
                  :loading="plansLoading"
                  :platform-name="personalSelected?.name || ''"
                  @add-item="addCalcItem"
                />
                <p
                  v-if="personalSelected && platformBudgetWarning(personalSelected)"
                  class="budget-inline-warn"
                >
                  이 플랫폼 최저 요금제 추가 시 월 예산 {{ formatWon(monthlyBudget) }}원을 초과할 수 있습니다.
                </p>
              </div>
            </section>
          </div>

          <SubscriptionCalculator
            v-model="calcItems"
            :existing-monthly="existingMonthly"
            :monthly-budget="monthlyBudget"
            @drop-plan="onCalcDropItem"
          />
        </template>
      </template>
    </template>
  </main>
</template>

<style scoped>
.benchmark-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 48px;
}

.tab-nav {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tab-btn {
  padding: 10px 16px;
  border: 1px solid var(--ws-border);
  border-radius: 999px;
  background: var(--ws-surface-2);
  cursor: pointer;
  font-weight: 600;
}

.tab-btn.active {
  border-color: var(--ws-primary);
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
}

.meta-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--ws-muted);
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
  padding: 18px;
}

.chart-block h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.benchmark-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
  gap: 20px;
  align-items: start;
}

.leaderboard-panel h2,
.detail-panel h2 {
  margin: 0 0 16px;
  font-size: 18px;
}

.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.rank-item {
  list-style: none;
}

.rank-button {
  width: 100%;
  display: grid;
  grid-template-columns: 28px 36px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--ws-border);
  border-radius: 12px;
  background: var(--ws-surface-2);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  text-decoration: none;
}

.rank-item.active .rank-button,
.rank-button:hover {
  border-color: var(--ws-primary);
  background: var(--ws-surface);
}

.rank-num { font-weight: 700; color: var(--ws-muted); }

.platform-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: contain;
}

.platform-icon.lg { width: 48px; height: 48px; }

.platform-icon.fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--ws-surface);
  border: 1px solid var(--ws-border);
  font-weight: 700;
}

.rank-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.rank-score { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; min-width: 72px; }
.rank-score strong { font-size: 18px; color: var(--ws-primary); }

.score-bar {
  height: 6px;
  width: 72px;
  border-radius: 999px;
  background: var(--ws-border);
  overflow: hidden;
}

.score-bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--ws-primary), var(--ws-secondary));
}

.detail-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.detail-head h2 { margin: 0; }

.confidence-badge {
  margin-left: auto;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--ws-surface-2);
  border: 1px solid var(--ws-border);
}

.confidence-badge[data-level='high'] { color: #0f766e; border-color: #99f6e4; background: #ecfdf5; }
.confidence-badge[data-level='medium'] { color: #b45309; border-color: #fde68a; background: #fffbeb; }

.axis-grid { display: grid; gap: 10px; }

.axis-row {
  display: grid;
  grid-template-columns: 72px 1fr 44px;
  gap: 10px;
  align-items: center;
}

.axis-label {
  display: flex;
  align-items: center;
  gap: 5px;
}

.info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--ws-border);
  color: var(--ws-muted);
  font-size: 10px;
  font-weight: 700;
  cursor: help;
  position: relative;
  flex-shrink: 0;
}

.info-icon .tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: 140%;
  left: 0;
  width: 200px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #17202a;
  color: #fff;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.45;
  text-align: left;
  z-index: 30;
  transition: opacity 0.15s ease;
  pointer-events: none;
}

.info-icon:hover .tooltip,
.info-icon.active .tooltip {
  visibility: visible;
  opacity: 1;
}
.axis-value { font-size: 13px; font-weight: 600; text-align: right; }

.axis-bar {
  height: 6px;
  border-radius: 999px;
  background: var(--ws-border);
  overflow: hidden;
}

.axis-bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--ws-primary), var(--ws-secondary));
}

.auth-prompt { padding: 24px; text-align: center; }
.pref-actions { display: flex; gap: 10px; margin-bottom: 16px; }
.taste-summary { padding: 18px; margin-bottom: 16px; }
.taste-summary h3 { margin: 0 0 8px; font-size: 15px; }
.small { font-size: 13px; }

.score-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 20px;
}

.score-pills span {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--ws-surface-2);
  border: 1px solid var(--ws-border);
  font-size: 13px;
}

.report-panel h3 { margin: 20px 0 10px; font-size: 15px; }

.reason-list,
.genre-match-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.title-section {
  margin-top: 24px;
}

.title-section h3 {
  margin: 0 0 6px;
  font-size: 15px;
}

.title-strip {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 8px 2px 12px;
  margin-top: 10px;
  scroll-snap-type: x mandatory;
}

.title-card {
  flex: 0 0 108px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-decoration: none;
  color: inherit;
  scroll-snap-align: start;
  position: relative;
}

.title-card img,
.title-poster-fallback {
  width: 108px;
  height: 162px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid var(--ws-border);
  background: var(--ws-surface-2);
}

.title-poster-fallback {
  display: grid;
  place-items: center;
  padding: 8px;
  font-size: 12px;
  text-align: center;
  color: var(--ws-muted);
}

.title-card strong {
  font-size: 12px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.title-meta {
  font-size: 11px;
  color: var(--ws-muted);
}

.badge.exclusive {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 1;
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
}

.budget-hint { margin-bottom: 10px; }

.budget-banner-warn,
.budget-inline-warn {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 600;
}

.budget-chip {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: #fef2f2;
  color: #b91c1c;
}

.plan-section {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--ws-border);
}

.plan-section h3 {
  margin: 0 0 6px;
  font-size: 15px;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.plan-card {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
  text-align: left;
  cursor: grab;
  color: inherit;
  font: inherit;
}

.plan-card:active {
  cursor: grabbing;
}

.plan-card strong {
  font-size: 14px;
}

@media (max-width: 860px) {
  .benchmark-layout { grid-template-columns: 1fr; }
  .confidence-badge { display: none; }
}
</style>
