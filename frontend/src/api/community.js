import { apiRequest } from './http';

export async function fetchCommunityBoards() {
  const data = await apiRequest('/api/community/boards/');
  return data.boards || [];
}

export async function fetchCommunityPosts({ board, platformId = '', flairTag = '', noFlair = false, q = '' } = {}) {
  const params = new URLSearchParams();
  if (board) params.set('board', board);
  if (platformId) params.set('platform_id', platformId);
  if (flairTag) params.set('flair_tag', flairTag);
  if (noFlair) params.set('no_flair', '1');
  if (q) params.set('q', q);

  const query = params.toString();
  return apiRequest(`/api/community/posts/${query ? `?${query}` : ''}`);
}

export async function fetchMyCommunityPosts({ board } = {}) {
  const params = new URLSearchParams({ mine: '1' });
  if (board) params.set('board', board);
  return apiRequest(`/api/community/posts/?${params.toString()}`);
}

export async function createCommunityPost(body) {
  return apiRequest('/api/community/posts/', {
    method: 'POST',
    body,
  });
}

export async function fetchCommunityPost(postId) {
  return apiRequest(`/api/community/posts/${postId}/`);
}

export async function updateCommunityPost(postId, { title, content }) {
  return apiRequest(`/api/community/posts/${postId}/`, {
    method: 'PATCH',
    body: { title, content },
  });
}

export async function deleteCommunityPost(postId) {
  return apiRequest(`/api/community/posts/${postId}/`, {
    method: 'DELETE',
    body: {},
  });
}

export async function updateCommunityPostReaction(postId, reaction) {
  return apiRequest(`/api/community/posts/${postId}/reaction/`, {
    method: 'POST',
    body: { reaction },
  });
}

export async function reportCommunityPost(postId) {
  return apiRequest(`/api/community/posts/${postId}/report/`, {
    method: 'POST',
    body: {},
  });
}

export async function addCommunityComment(postId, content) {
  return apiRequest(`/api/community/posts/${postId}/comments/`, {
    method: 'POST',
    body: { content },
  });
}

export async function updateCommunityComment(commentId, content) {
  return apiRequest(`/api/community/comments/${commentId}/`, {
    method: 'PATCH',
    body: { content },
  });
}

export async function deleteCommunityComment(commentId) {
  return apiRequest(`/api/community/comments/${commentId}/`, {
    method: 'DELETE',
    body: {},
  });
}

export async function updateCommunityCommentReaction(commentId, reaction) {
  return apiRequest(`/api/community/comments/${commentId}/reaction/`, {
    method: 'POST',
    body: { reaction },
  });
}

export async function reportCommunityComment(commentId) {
  return apiRequest(`/api/community/comments/${commentId}/report/`, {
    method: 'POST',
    body: {},
  });
}
