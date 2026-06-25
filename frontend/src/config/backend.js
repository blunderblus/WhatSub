export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export const backendRoutes = {
  onboarding: '/accounts/onboarding/',
  onboardingGmail: '/accounts/onboarding/gmail/',
  onboardingManual: '/accounts/onboarding/manual/',
  onboardingComplete: '/accounts/onboarding/complete/',
  googleAuthDone: '/accounts/auth/google/done/',
  googleAuthStart: '/accounts/auth/google/start/',
  googleLogin: '/accounts/google/login/',
};

export function backendUrl(path) {
  return `${BACKEND_URL}${path}`;
}

export function redirectToBackend(path) {
  window.location.href = backendUrl(path);
}

/** Start Google OAuth. intent: 'login' | 'signup' */
export function googleAuthUrl(nextPath = backendRoutes.googleAuthDone, intent = 'signup') {
  const params = new URLSearchParams({
    next: backendUrl(nextPath),
    intent,
  });
  return `${backendUrl(backendRoutes.googleAuthStart)}?${params.toString()}`;
}
