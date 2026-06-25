import { BACKEND_URL } from '../config/backend';

/** Resolve API asset paths (/media/...) to the backend origin for cross-origin deploys. */
export function resolveAssetUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith('/')) {
    return `${BACKEND_URL.replace(/\/$/, '')}${url}`;
  }
  return url;
}
