import { apiRequest } from './http';
import { createTtlCache } from '../utils/ttlCache';

const CATALOG_CACHE_TTL_MS = 5 * 60 * 1000;
const catalogCache = createTtlCache(CATALOG_CACHE_TTL_MS);

const CONTENT_ENDPOINTS = {
  movies: {
    list: '/api/contents/movie_list/',
    genres: '/api/contents/genres/',
    detail: (id) => `/api/contents/movie_detail/${id}/`,
    mediaType: 'movie',
  },
  shows: {
    list: '/api/contents/show_list/',
    genres: '/api/contents/show_genres/',
    detail: (id) => `/api/contents/show_detail/${id}/`,
    mediaType: 'tv',
  },
};

export function normalizeContentKind(kind) {
  return kind === 'shows' ? 'shows' : 'movies';
}

export function mediaTypeForKind(kind) {
  return endpointFor(kind).mediaType;
}

export async function fetchContentGenres(kind) {
  const data = await catalogCache.getOrSet(`genres:${normalizeContentKind(kind)}`, () => (
    apiRequest(endpointFor(kind).genres)
  ));
  return data.genres || [];
}

export async function fetchStreamingPlatforms(mediaType) {
  const data = await catalogCache.getOrSet(`platforms:${mediaType}`, () => (
    apiRequest(`/api/contents/streaming_platforms/?media_type=${mediaType}`)
  ));
  return data.platforms || [];
}

export async function fetchContentList({ kind, page = 1, genre = '', platformIds = [], live = false }) {
  const params = new URLSearchParams({ page });
  if (genre) params.set('genre', genre);
  if (live) params.set('live', '1');
  for (const platformId of platformIds) {
    params.append('platform_id', platformId);
  }

  const normalizedKind = normalizeContentKind(kind);
  const url = `${endpointFor(normalizedKind).list}?${params.toString()}`;
  const data = live
    ? await apiRequest(url)
    : await catalogCache.getOrSet(`list:${normalizedKind}:${params.toString()}`, () => apiRequest(url));
  return {
    items: data.results || [],
    page: data.page || page,
    totalPages: Math.min(data.total_pages || 1, 500),
  };
}

export async function fetchStreamingProviders({ tmdbId, mediaType }) {
  const params = new URLSearchParams({
    tmdb_id: tmdbId,
    media_type: mediaType,
  });
  const data = await apiRequest(`/api/contents/streaming_info/?${params.toString()}`);
  return data.providers || [];
}

export function updateContentReaction({ tmdbId, mediaType, reaction, title = '', posterUrl = '' }) {
  return apiRequest(`/api/contents/reaction/${tmdbId}/`, {
    method: 'POST',
    body: {
      media_type: mediaType,
      reaction,
      title,
      poster_url: posterUrl,
    },
  });
}

function endpointFor(kind) {
  return CONTENT_ENDPOINTS[normalizeContentKind(kind)];
}
