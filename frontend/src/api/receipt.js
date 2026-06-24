import { apiRequest } from './http';

export function extractReceiptImages(files) {
  const form = new FormData();
  for (const file of files) {
    form.append('images', file);
  }
  return apiRequest('/api/accounts/receipt/extract/', {
    method: 'POST',
    body: form,
  });
}

export function saveDetectedSubscriptions(subscriptions, source = 'receipt') {
  return apiRequest('/api/accounts/onboarding/gmail/save-bulk/', {
    method: 'POST',
    body: { subscriptions, source },
  });
}
