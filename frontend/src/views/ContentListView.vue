<script setup>

import { computed, onMounted, ref, watch } from 'vue';

import { useRoute, useRouter } from 'vue-router';

import { apiRequest } from '../api/http';

import ContentCard from '../components/ContentCard.vue';

import PageHeader from '../components/PageHeader.vue';



const route = useRoute();

const router = useRouter();



const genres = ref([]);

const platforms = ref([]);

const items = ref([]);

const selectedGenre = ref('');

const selectedPlatforms = ref([]);

const currentPage = ref(1);

const totalPages = ref(1);

const loading = ref(false);

const error = ref('');



const isMovie = computed(() => route.params.type === 'movies');

const label = computed(() => (isMovie.value ? '영화' : '시리즈'));

const listUrl = computed(() => (isMovie.value ? '/api/contents/movie_list/' : '/api/contents/show_list/'));

const genresUrl = computed(() => (isMovie.value ? '/api/contents/genres/' : '/api/contents/show_genres/'));



const selectedGenreName = computed(() => {

  if (!selectedGenre.value) return `전체 ${label.value}`;

  return genres.value.find((genre) => String(genre.id) === String(selectedGenre.value))?.name || label.value;

});



const selectedPlatformNames = computed(() => {

  if (!selectedPlatforms.value.length) return [];

  return selectedPlatforms.value

    .map((id) => platforms.value.find((p) => String(p.platform_id) === String(id))?.name)

    .filter(Boolean);

});



const pageTitle = computed(() => {

  if (selectedPlatformNames.value.length) {

    return `${selectedPlatformNames.value.join(' · ')} · ${selectedGenreName.value}`;

  }

  return selectedGenreName.value;

});



function syncPlatformFromQuery() {

  const single = route.query.platform_id;

  const multi = route.query.platform_ids;

  if (Array.isArray(single)) {

    selectedPlatforms.value = single.map(String);

  } else if (single) {

    selectedPlatforms.value = [String(single)];

  } else if (multi) {

    selectedPlatforms.value = String(multi).split(',').map((s) => s.trim()).filter(Boolean);

  } else {

    selectedPlatforms.value = [];

  }

}



function updatePlatformQuery() {

  const query = { ...route.query };

  delete query.platform_id;

  delete query.platform_ids;

  if (selectedPlatforms.value.length === 1) {

    query.platform_id = selectedPlatforms.value[0];

  } else if (selectedPlatforms.value.length > 1) {

    query.platform_ids = selectedPlatforms.value.join(',');

  }

  router.replace({ path: route.path, query });

}



async function loadPlatforms() {
  const mediaType = isMovie.value ? 'movie' : 'tv';
  const data = await apiRequest(`/api/contents/streaming_platforms/?media_type=${mediaType}`);
  platforms.value = data.platforms || [];
}



async function loadGenres() {

  const data = await apiRequest(genresUrl.value);

  genres.value = data.genres || [];

}



async function loadItems(page = 1) {

  loading.value = true;

  error.value = '';

  const params = new URLSearchParams({ page });

  if (selectedGenre.value) params.set('genre', selectedGenre.value);

  for (const platformId of selectedPlatforms.value) {

    params.append('platform_id', platformId);

  }



  try {

    const data = await apiRequest(`${listUrl.value}?${params.toString()}`);

    items.value = data.results || [];

    currentPage.value = data.page || page;

    totalPages.value = Math.min(data.total_pages || 1, 500);

  } catch (err) {

    items.value = [];

    error.value = err.message;

  } finally {

    loading.value = false;

  }

}



function selectGenre(id) {

  selectedGenre.value = id;

  loadItems(1);

}



function isPlatformSelected(id) {

  return selectedPlatforms.value.includes(String(id));

}



function togglePlatform(id) {

  const sid = String(id);

  if (isPlatformSelected(sid)) {

    selectedPlatforms.value = selectedPlatforms.value.filter((x) => x !== sid);

  } else {

    selectedPlatforms.value = [...selectedPlatforms.value, sid];

  }

  updatePlatformQuery();

  loadItems(1);

}



function clearPlatforms() {

  selectedPlatforms.value = [];

  updatePlatformQuery();

  loadItems(1);

}



function changePage(offset) {

  const next = currentPage.value + offset;

  if (next < 1 || next > totalPages.value || loading.value) return;

  loadItems(next);

}



function openDetail(item) {

  router.push(`/contents/${route.params.type}/${item.tmdb_id}`);

}



watch(() => route.params.type, async () => {

  selectedGenre.value = '';

  syncPlatformFromQuery();

  await Promise.all([loadGenres(), loadPlatforms(), loadItems(1)]);

});



watch(

  () => [route.query.platform_id, route.query.platform_ids],

  () => {

    syncPlatformFromQuery();

    loadItems(1);

  },

);



onMounted(async () => {

  syncPlatformFromQuery();

  await Promise.all([loadGenres(), loadPlatforms(), loadItems()]);

});

</script>



<template>

  <main>

    <PageHeader :eyebrow="`WhatSub ${isMovie ? 'Movies' : 'Shows'}`" :title="pageTitle" />



    <div v-if="platforms.length" class="chip-row" style="margin-bottom: 14px">

      <span class="filter-label">플랫폼</span>

      <button class="chip" :class="{ active: selectedPlatforms.length === 0 }" type="button" @click="clearPlatforms">전체</button>

      <button

        v-for="p in platforms"

        :key="p.platform_id"

        class="chip"

        :class="{ active: isPlatformSelected(p.platform_id) }"

        type="button"

        @click="togglePlatform(String(p.platform_id))"

      >

        {{ p.name }} ({{ p.title_count }})

      </button>

    </div>

    <p v-if="selectedPlatforms.length > 1" class="filter-hint muted">선택한 플랫폼 중 하나라도 시청 가능한 작품을 표시합니다.</p>



    <div class="chip-row" style="margin-bottom: 22px">

      <span class="filter-label">장르</span>

      <button class="chip" :class="{ active: selectedGenre === '' }" type="button" @click="selectGenre('')">전체</button>

      <button

        v-for="genre in genres"

        :key="genre.id"

        class="chip"

        :class="{ active: String(selectedGenre) === String(genre.id) }"

        type="button"

        @click="selectGenre(genre.id)"

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

        :media-type="isMovie ? 'movie' : 'tv'"

        @open="openDetail"

      />

    </div>



    <nav class="pagination" aria-label="목록 페이지">

      <button class="button" type="button" :disabled="currentPage <= 1 || loading" @click="changePage(-1)">이전</button>

      <span>{{ currentPage }} / {{ totalPages }}</span>

      <button class="button" type="button" :disabled="currentPage >= totalPages || loading" @click="changePage(1)">다음</button>

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

