<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import ContentCard from '../components/ContentCard.vue';
import PageHeader from '../components/PageHeader.vue';

const route = useRoute();
const router = useRouter();

const genres = ref([]);
const items = ref([]);
const selectedGenre = ref('');
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

async function loadGenres() {
  const data = await apiRequest(genresUrl.value);
  genres.value = data.genres || [];
}

async function loadItems(page = 1) {
  loading.value = true;
  error.value = '';
  const params = new URLSearchParams({ page });
  if (selectedGenre.value) params.set('genre', selectedGenre.value);

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
  await Promise.all([loadGenres(), loadItems(1)]);
});

onMounted(async () => {
  await Promise.all([loadGenres(), loadItems()]);
});
</script>

<template>
  <main>
    <PageHeader :eyebrow="`WhatSub ${isMovie ? 'Movies' : 'Shows'}`" :title="selectedGenreName" />

    <div class="chip-row" style="margin-bottom: 22px">
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
      <ContentCard v-for="item in items" :key="item.tmdb_id" :item="item" @open="openDetail" />
    </div>

    <nav class="pagination" aria-label="목록 페이지">
      <button class="button" type="button" :disabled="currentPage <= 1 || loading" @click="changePage(-1)">이전</button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button class="button" type="button" :disabled="currentPage >= totalPages || loading" @click="changePage(1)">다음</button>
    </nav>
  </main>
</template>
