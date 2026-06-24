import { computed, ref } from 'vue';
import {
  fetchContentGenres,
  fetchContentList,
  fetchStreamingPlatforms,
  mediaTypeForKind,
} from '../api/contents';
import { platformIdsToQuery, selectedPlatformIdsFromQuery } from '../utils/routeQuery';

const CONTENT_LABELS = {
  movies: '영화',
  shows: '시리즈',
};

export function useContentCatalog(kind) {
  const genres = ref([]);
  const platforms = ref([]);
  const items = ref([]);
  const selectedGenre = ref('');
  const selectedPlatforms = ref([]);
  const currentPage = ref(1);
  const totalPages = ref(1);
  const loading = ref(false);
  const error = ref('');

  const label = computed(() => CONTENT_LABELS[kind.value] || CONTENT_LABELS.movies);
  const selectedGenreName = computed(() => {
    if (!selectedGenre.value) return label.value;
    return genres.value.find((genre) => String(genre.id) === String(selectedGenre.value))?.name || label.value;
  });
  const selectedPlatformNames = computed(() => (
    selectedPlatforms.value
      .map((id) => platforms.value.find((platform) => String(platform.platform_id) === String(id))?.name)
      .filter(Boolean)
  ));
  const pageTitle = computed(() => {
    if (!selectedPlatformNames.value.length) return selectedGenreName.value;
    return `${selectedPlatformNames.value.join(' · ')} · ${selectedGenreName.value}`;
  });

  function syncPlatformsFromQuery(query) {
    selectedPlatforms.value = selectedPlatformIdsFromQuery(query);
  }

  function syncGenreFromQuery(query) {
    selectedGenre.value = query.genre ? String(query.genre) : '';
  }

  function platformQuery() {
    return platformIdsToQuery(selectedPlatforms.value);
  }

  async function loadGenres() {
    genres.value = await fetchContentGenres(kind.value);
  }

  async function loadPlatforms() {
    platforms.value = await fetchStreamingPlatforms(mediaTypeForKind(kind.value));
  }

  async function loadItems(page = 1) {
    loading.value = true;
    error.value = '';
    try {
      const result = await fetchContentList({
        kind: kind.value,
        page,
        genre: selectedGenre.value,
        platformIds: selectedPlatforms.value,
      });
      items.value = result.items;
      currentPage.value = result.page;
      totalPages.value = result.totalPages;
    } catch (err) {
      items.value = [];
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  }

  async function reset(page = 1) {
    await Promise.all([loadGenres(), loadPlatforms()]);
    await loadItems(page);
  }

  async function selectGenre(id) {
    selectedGenre.value = id;
    await loadItems(1);
  }

  async function changePage(offset) {
    const next = currentPage.value + offset;
    if (next < 1 || next > totalPages.value || loading.value) return;
    await loadItems(next);
  }

  function isPlatformSelected(id) {
    return selectedPlatforms.value.includes(String(id));
  }

  async function togglePlatform(id) {
    const platformId = String(id);
    selectedPlatforms.value = isPlatformSelected(platformId)
      ? selectedPlatforms.value.filter((selectedId) => selectedId !== platformId)
      : [...selectedPlatforms.value, platformId];
    await loadItems(1);
  }

  async function clearPlatforms() {
    selectedPlatforms.value = [];
    await loadItems(1);
  }

  return {
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
    pageTitle,
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
  };
}
