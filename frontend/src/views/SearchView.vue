<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import ContentCard from '../components/ContentCard.vue';
import PageHeader from '../components/PageHeader.vue';

const router = useRouter();

const query = ref('');
const results = ref([]);
const loading = ref(false);
const error = ref('');

async function search() {
  if (!query.value.trim()) return;
  loading.value = true;
  error.value = '';

  try {
    const data = await apiRequest(`/api/contents/tmdb_search/?query=${encodeURIComponent(query.value.trim())}`);
    results.value = data.results || [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function openDetail(item) {
  router.push(`/contents/${item.media_type === 'tv' ? 'shows' : 'movies'}/${item.tmdb_id}`);
}
</script>

<template>
  <main class="ws-page">
    <section class="panel">
      <PageHeader
        eyebrow="Search"
        title="작품 검색"
        description="영화와 시리즈를 검색하고 한국에서 볼 수 있는 OTT를 확인하세요."
      />
      <form class="search-form" @submit.prevent="search">
        <input v-model="query" placeholder="작품 제목을 입력하세요" aria-label="작품 제목" />
        <button class="button primary" type="submit">검색</button>
      </form>
    </section>

    <p v-if="error" class="notice" style="margin-top: 18px">{{ error }}</p>
    <div v-else-if="loading" class="loader" style="margin-top: 18px">검색 중입니다.</div>
    <div v-else-if="results.length === 0" class="empty" style="margin-top: 18px">검색 결과가 여기에 표시됩니다.</div>
    <div v-else class="poster-grid" style="margin-top: 18px">
      <ContentCard v-for="item in results" :key="`${item.media_type}-${item.tmdb_id}`" :item="item" compact @open="openDetail" />
    </div>
  </main>
</template>

<style scoped>
.search-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  margin-top: 20px;
}

.search-form input {
  min-height: 46px;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
}

@media (max-width: 560px) {
  .search-form {
    grid-template-columns: 1fr;
  }
}
</style>
