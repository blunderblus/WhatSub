import { defineStore } from 'pinia';
import { apiRequest } from '../api/http';

export const useSessionStore = defineStore('session', {
  state: () => ({
    loading: true,
    isAuthenticated: false,
    user: null,
  }),
  actions: {
    async refresh() {
      this.loading = true;
      const data = await apiRequest('/api/accounts/me/');
      this.isAuthenticated = data.isAuthenticated;
      this.user = data.user || null;
      this.loading = false;
    },
    async login(credentials) {
      await apiRequest('/api/accounts/login/', {
        method: 'POST',
        body: credentials,
      });
      await this.refresh();
    },
    async signup(payload) {
      await apiRequest('/api/accounts/signup/', {
        method: 'POST',
        body: payload,
      });
      await this.refresh();
    },
    async logout() {
      await apiRequest('/api/accounts/logout/', {
        method: 'POST',
        body: {},
      });
      this.isAuthenticated = false;
      this.user = null;
    },
  },
});
