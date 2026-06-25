import { apiRequest } from './http';

export function fetchBenchmarkLeaderboard() {
  return apiRequest('/api/contents/benchmark/?min_titles=1');
}

export function fetchBenchmarkPlatform(platformId) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/`);
}

export function fetchPersonalBenchmark({ useLlm = false } = {}) {
  const params = new URLSearchParams({ use_llm: useLlm ? '1' : '0' });
  return apiRequest(`/api/contents/benchmark/personal/?${params.toString()}`);
}

export function fetchBenchmarkPlatformPage(platformId, { useLlm = false } = {}) {
  const params = new URLSearchParams({ use_llm: useLlm ? '1' : '0' });
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/page/?${params.toString()}`);
}

export function fetchBenchmarkPlatformInsight(platformId) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/insight/`);
}

export function saveBenchmarkPlatformReview(platformId, { score, body }) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/reviews/`, {
    method: 'POST',
    body: { score, body },
  });
}

export function deleteBenchmarkPlatformReview(platformId) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/reviews/me/`, {
    method: 'DELETE',
    body: {},
  });
}

export function reactBenchmarkPlatformReview(platformId, reviewId, reaction) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/reviews/${reviewId}/reaction/`, {
    method: 'POST',
    body: { reaction },
  });
}

export function addBenchmarkReviewComment(platformId, reviewId, content) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/reviews/${reviewId}/comments/`, {
    method: 'POST',
    body: { content },
  });
}

export function deleteBenchmarkReviewComment(platformId, commentId) {
  return apiRequest(`/api/contents/benchmark/platforms/${platformId}/reviews/comments/${commentId}/`, {
    method: 'DELETE',
    body: {},
  });
}

export function fetchPlatformCatalog(platformId) {
  return apiRequest(`/api/subscriptions/platforms/${platformId}/catalog/`);
}
