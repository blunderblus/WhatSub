<script setup>
import { computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ContentCard from '../components/ContentCard.vue';
import { mediaTypeForKind } from '../api/contents';
import { useContentCatalog } from '../composables/useContentCatalog';
import { positivePageFromQuery } from '../utils/routeQuery';

const route = useRoute();
const router = useRouter();
const contentKind = computed(() => (route.params.type === 'shows' ? 'shows' : 'movies'));

const {
  genres,
  platforms,
  items,
  selectedGenre,
  selectedPlatforms,
  currentPage,
  totalPages,
  loading,
  error,
  label,
  syncPlatformsFromQuery,
  syncGenreFromQuery,
  platformQuery,
  reset,
  selectGenre,
  changePage,
  isPlatformSelected,
  togglePlatform,
  clearPlatforms,
  loadItems,
} = useContentCatalog(contentKind);

function syncFiltersFromQuery() {
  syncPlatformsFromQuery(route.query);
  syncGenreFromQuery(route.query);
}

function listQuery(page = currentPage.value) {
  const query = { ...platformQuery() };
  if (selectedGenre.value) {
    query.genre = selectedGenre.value;
  }
  if (page > 1) {
    query.page = String(page);
  }
  return query;
}

function replaceListQuery(page = currentPage.value) {
  router.replace({ path: route.path, query: listQuery(page) });
}

async function selectPlatform(id) {
  await togglePlatform(id);
  replaceListQuery(1);
}

async function clearPlatformSelection() {
  await clearPlatforms();
  replaceListQuery(1);
}

async function selectContentGenre(id) {
  await selectGenre(id);
  replaceListQuery(1);
}

async function changeContentPage(offset) {
  await changePage(offset);
  replaceListQuery();
}

function openDetail(item) {
  router.push({
    path: `/contents/${route.params.type}/${item.tmdb_id}`,
    query: listQuery(currentPage.value),
  });
}

watch(() => route.params.type, async () => {
  syncFiltersFromQuery();
  await reset(positivePageFromQuery(route.query));
});

watch(
  () => [route.query.platform_id, route.query.platform_ids, route.query.genre],
  async () => {
    syncFiltersFromQuery();
    await loadItems(positivePageFromQuery(route.query));
  },
);

onMounted(async () => {
  syncFiltersFromQuery();
  await reset(positivePageFromQuery(route.query));
});
</script>

<template>
  <main class="ws-page">
    <div v-if="platforms.length" class="chip-row" style="margin-bottom: 14px">
      <span class="filter-label">플랫폼</span>
      <button class="chip" :class="{ active: selectedPlatforms.length === 0 }" type="button" @click="clearPlatformSelection">
        전체
      </button>
      <button
        v-for="platform in platforms"
        :key="platform.platform_id"
        class="chip"
        :class="{ active: isPlatformSelected(platform.platform_id) }"
        type="button"
        @click="selectPlatform(platform.platform_id)"
      >
        {{ platform.name }} ({{ platform.title_count }})
      </button>
    </div>
    <p v-if="selectedPlatforms.length > 1" class="filter-hint muted">선택한 플랫폼 중 하나라도 시청 가능한 작품을 표시합니다.</p>

    <div class="chip-row" style="margin-bottom: 22px">
      <span class="filter-label">장르</span>
      <button class="chip" :class="{ active: selectedGenre === '' }" type="button" @click="selectContentGenre('')">전체</button>
      <button
        v-for="genre in genres"
        :key="genre.id"
        class="chip"
        :class="{ active: String(selectedGenre) === String(genre.id) }"
        type="button"
        @click="selectContentGenre(genre.id)"
      >
        {{ genre.name }}
      </button>
    </div>

    <p v-if="error" class="notice">{{ error }}</p>
    <div v-else-if="loading" class="loader">{{ label }} 목록을 불러오는 중입니다.</div>
    <div v-else-if="items.length === 0" class="empty">표시할 콘텐츠가 없습니다.</div>
    <div v-else class="poster-grid">
      <ContentCard
        v-for="item in items"
        :key="item.tmdb_id"
        :item="item"
        :media-type="mediaTypeForKind(contentKind)"
        @open="openDetail"
      />
    </div>

    <nav class="pagination" aria-label="목록 페이지">
      <button class="button" type="button" :disabled="currentPage <= 1 || loading" @click="changeContentPage(-1)">이전</button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button class="button" type="button" :disabled="currentPage >= totalPages || loading" @click="changeContentPage(1)">다음</button>
    </nav>
  </main>
</template>

<style scoped>
.filter-label {
  align-self: center;
  font-size: 13px;
  color: var(--ws-muted);
  margin-right: 4px;
}

.filter-hint {
  margin: -6px 0 14px;
  font-size: 13px;
}
</style>
