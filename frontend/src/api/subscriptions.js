import { apiRequest } from './http';

export function fetchSubscriptionPlatforms() {
  return apiRequest('/api/subscriptions/platforms/');
}

export function fetchSubscriptionPlans() {
  return apiRequest('/api/subscriptions/plans/');
}

export function fetchUserSubscriptionDashboard() {
  return apiRequest('/api/accounts/dashboard/');
}

export function createUserSubscription(payload) {
  return apiRequest('/api/accounts/subscriptions/', {
    method: 'POST',
    body: payload,
  });
}
