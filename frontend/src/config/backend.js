export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export const backendRoutes = {
  onboarding: '/accounts/onboarding/',
  onboardingGmail: '/accounts/onboarding/gmail/',
  onboardingManual: '/accounts/onboarding/manual/',
  onboardingComplete: '/accounts/onboarding/complete/',
};

export function backendUrl(path) {
  return `${BACKEND_URL}${path}`;
}

export function redirectToBackend(path) {
  window.location.href = backendUrl(path);
}
