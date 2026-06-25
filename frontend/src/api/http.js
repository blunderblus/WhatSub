import { BACKEND_URL } from '../config/backend';

let csrfPromise = null;

function resetCsrfToken() {
  csrfPromise = null;
}

function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const base = BACKEND_URL.replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalized}`;
}

async function csrfToken() {
  if (!csrfPromise) {
    csrfPromise = fetch(apiUrl('/api/accounts/csrf/'), { credentials: 'include' })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('CSRF token fetch failed');
        }
        const data = await response.json();
        return data.csrfToken;
      })
      .catch((error) => {
        csrfPromise = null;
        throw error;
      });
  }
  return csrfPromise;
}

function isCsrfFailure(status, data) {
  if (status !== 403) return false;
  const message = String(data?.detail || data?.error || '');
  return message.toLowerCase().includes('csrf');
}

export async function apiRequest(path, options = {}, retried = false) {
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

  const response = await fetch(apiUrl(path), {
    credentials: 'include',
    ...options,
    headers,
    body: options.body && !(options.body instanceof FormData)
      ? JSON.stringify(options.body)
      : options.body,
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));

  if (!response.ok) {
    if (!retried && isCsrfFailure(response.status, data)) {
      resetCsrfToken();
      return apiRequest(path, options, true);
    }
    const error = new Error(data?.detail || data?.error || '요청을 처리하지 못했습니다.');
    error.payload = data;
    throw error;
  }

  return data;
}
