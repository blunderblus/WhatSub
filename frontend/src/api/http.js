let csrfPromise = null;

async function csrfToken() {
  if (!csrfPromise) {
    csrfPromise = fetch('/api/accounts/csrf/', { credentials: 'include' })
      .then((response) => response.json())
      .then((data) => data.csrfToken);
  }
  return csrfPromise;
}

export async function apiRequest(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    ...(options.headers || {}),
  };

  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (!['GET', 'HEAD', undefined].includes(options.method)) {
    headers['X-CSRFToken'] = await csrfToken();
  }

  const response = await fetch(path, {
    credentials: 'include',
    ...options,
    headers,
    body: options.body && !(options.body instanceof FormData)
      ? JSON.stringify(options.body)
      : options.body,
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(data?.detail || data?.error || '요청을 처리하지 못했습니다.');
    error.payload = data;
    throw error;
  }

  return data;
}
