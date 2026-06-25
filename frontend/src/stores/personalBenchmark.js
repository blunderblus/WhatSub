import { defineStore } from 'pinia';
import { fetchPersonalBenchmark } from '../api/benchmark';

export const usePersonalBenchmarkStore = defineStore('personalBenchmark', {
  state: () => ({
    data: null,
    loading: false,
    error: '',
  }),
  actions: {
    async load({ refresh = false } = {}) {
      if (refresh) {
        this.data = null;
      }
      if (!refresh && this.data) {
        return this.data;
      }
      this.loading = true;
      this.error = '';
      try {
        this.data = await fetchPersonalBenchmark({ useLlm: refresh });
        return this.data;
      } catch (err) {
        this.data = null;
        this.error = err.message || '추천 리포트를 불러오지 못했습니다.';
        throw err;
      } finally {
        this.loading = false;
      }
    },
    clear() {
      this.data = null;
      this.error = '';
    },
  },
});
