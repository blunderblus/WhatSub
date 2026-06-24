import { computed, ref } from 'vue';
import { fetchBenchmarkLeaderboard } from '../api/benchmark';
import {
  fetchContentList,
  mediaTypeForKind,
} from '../api/contents';

const HOME_PLATFORM_LIMIT = 3;
const TITLES_PER_PLATFORM = 4;

function normalizeItems(items, kind) {
  return items.map((item) => ({
    ...item,
    kind,
    media_type: mediaTypeForKind(kind),
  }));
}

function uniqueTitles(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.media_type}-${item.tmdb_id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function sortByPopularity(items) {
  return [...items].sort((a, b) => {
    const popularityGap = Number(b.popularity || 0) - Number(a.popularity || 0);
    if (popularityGap !== 0) return popularityGap;
    return Number(b.rating || 0) - Number(a.rating || 0);
  });
}

async function fetchPlatformTitles(platform) {
  const [movies, shows] = await Promise.all([
    fetchContentList({ kind: 'movies', page: 1, platformIds: [platform.platform_id], live: true }),
    fetchContentList({ kind: 'shows', page: 1, platformIds: [platform.platform_id], live: true }),
  ]);

  const titles = uniqueTitles([
    ...normalizeItems(movies.items, 'movies'),
    ...normalizeItems(shows.items, 'shows'),
  ]);

  const visibleTitles = sortByPopularity(titles).slice(0, TITLES_PER_PLATFORM);
  return visibleTitles;
}

function buildRecommendation(platform, index) {
  const reasons = [
    '작품 풀이 넓어 처음 고르기 좋습니다.',
    '화제작을 빠르게 둘러보기 좋습니다.',
    '취향을 찾기 전에 후보로 두기 좋습니다.',
  ];

  return {
    ...platform,
    reason: reasons[index] || reasons[reasons.length - 1],
  };
}

export function useHomeDiscovery() {
  const platformGroups = ref([]);
  const platformRecommendations = ref([]);
  const loading = ref(false);
  const error = ref('');

  const hasPlatformGroups = computed(() =>
    platformGroups.value.some((group) => group.items.length > 0),
  );

  async function loadPlatformGroups(platforms) {
    const groups = await Promise.all(
      platforms.map(async (platform) => ({
        ...platform,
        items: await fetchPlatformTitles(platform),
      })),
    );

    platformGroups.value = groups.filter((group) => group.items.length > 0);
  }

  async function loadLeaderboardRecommendations() {
    const data = await fetchBenchmarkLeaderboard();
    return (data.platforms || [])
      .slice(0, 3)
      .map(buildRecommendation);
  }

  async function loadHomeDiscovery() {
    loading.value = true;
    error.value = '';
    try {
      const recommendations = await loadLeaderboardRecommendations();
      platformRecommendations.value = recommendations;
      await loadPlatformGroups(recommendations.slice(0, HOME_PLATFORM_LIMIT));
    } catch (err) {
      platformGroups.value = [];
      platformRecommendations.value = [];
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  }

  return {
    platformGroups,
    platformRecommendations,
    loading,
    error,
    hasPlatformGroups,
    loadHomeDiscovery,
  };
}
