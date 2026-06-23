<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { apiRequest } from '../api/http';

const route = useRoute();
const movie = ref(null);
const providers = ref([]);
const loading = ref(true);
const error = ref('');

const isMovie = computed(() => route.params.type === 'movies');
const detailUrl = computed(() => `/api/contents/${isMovie.value ? 'movie_detail' : 'show_detail'}/${route.params.id}/`);

const SUBSCRIPTION_TYPES = new Set(['subscription', 'free', 'ads']);
const TRANSACTION_TYPES = new Set(['rent', 'buy']);

const PLATFORM_HOME = {
  tving: 'https://www.tving.com',
  wavve: 'https://www.wavve.com',
  watcha: 'https://watcha.com',
  netflix: 'https://www.netflix.com',
  'disney+': 'https://www.disneyplus.com',
  'prime video': 'https://www.primevideo.com',
  'amazon prime video': 'https://www.primevideo.com',
};

const subscriptionProviders = computed(() =>
  providers.value.filter((p) => SUBSCRIPTION_TYPES.has(p.type)),
);
const transactionProviders = computed(() =>
  providers.value.filter((p) => TRANSACTION_TYPES.has(p.type)),
);

function providerInitial(name) {
  return (name || '?').trim().charAt(0).toUpperCase();
}

function resolveProviderHref(provider) {
  const link = (provider?.link || '').trim();
  if (link) return link;
  const key = (provider?.service || provider?.display_name || '').toLowerCase().trim();
  return PLATFORM_HOME[key] || '';
}

function openProvider(event, provider) {
  const href = resolveProviderHref(provider);
  if (!href) {
    event.preventDefault();
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  window.open(href, '_blank', 'noopener,noreferrer');
}

function hasDeepLink(provider) {
  return Boolean((provider?.link || '').trim());
}

function formatLicenseExpiry(expiresOn) {
  if (!expiresOn) return '';
  const parsed = new Date(expiresOn);
  if (Number.isNaN(parsed.getTime())) return `라이선스 ~${expiresOn}까지`;
  return `라이선스 ~${parsed.toLocaleDateString('ko-KR')}까지`;
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const data = await apiRequest(detailUrl.value);
    movie.value = data.movie;
    providers.value = data.providers || [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

watch(() => route.params.id, load);
onMounted(load);
</script>

<template>
  <main>
    <RouterLink class="button" :to="`/contents/${route.params.type}`">목록으로</RouterLink>
    <p v-if="error" class="notice" style="margin-top: 18px">{{ error }}</p>
    <div v-else-if="loading" class="loader" style="margin-top: 18px">상세 정보를 불러오는 중입니다.</div>

    <template v-else-if="movie">
      <section class="detail-hero" :style="{ '--backdrop': movie.backdrop_url ? `url(${movie.backdrop_url})` : 'none' }">
        <img v-if="movie.poster_url" class="detail-poster" :src="movie.poster_url" :alt="movie.title" />
        <div v-else class="detail-empty">{{ movie.title }}</div>
        <div class="detail-copy">
          <h1>{{ movie.title }}</h1>
          <div class="chip-row">
            <span class="detail-chip">{{ movie.release_date || '공개일 미정' }}</span>
            <span v-if="movie.runtime" class="detail-chip">{{ movie.runtime }}분</span>
            <span class="detail-chip">평점 {{ Number(movie.rating).toFixed(1) }}</span>
            <span v-for="genre in movie.genres" :key="genre.id" class="detail-chip">{{ genre.name }}</span>
          </div>
          <p>{{ movie.overview }}</p>
        </div>
      </section>

      <section class="panel" style="margin-top: 24px">
        <h2>이용 가능한 서비스</h2>
        <template v-if="providers.length">
          <div v-if="subscriptionProviders.length" class="provider-section">
            <h3>구독 · 무료</h3>
            <div class="provider-grid">
              <a
                v-for="(provider, index) in subscriptionProviders"
                :key="`sub-${index}-${provider.service}-${provider.type}`"
                class="provider-link"
                :class="{ 'no-link': !hasDeepLink(provider) }"
                :href="resolveProviderHref(provider) || '#'"
                target="_blank"
                rel="noopener noreferrer"
                @click="openProvider($event, provider)"
              >
                <img v-if="provider.icon_url" :src="provider.icon_url" :alt="provider.display_name || provider.service" />
                <span v-else class="provider-fallback">{{ providerInitial(provider.display_name || provider.service) }}</span>
            <strong>{{ provider.display_name || provider.service }}</strong>
            <span>
              {{ provider.type_label }}
              <template v-if="formatLicenseExpiry(provider.expires_on)"> · {{ formatLicenseExpiry(provider.expires_on) }}</template>
              <template v-else-if="!hasDeepLink(provider)"> · 작품 링크 없음</template>
            </span>
              </a>
            </div>
          </div>

          <div v-if="transactionProviders.length" class="provider-section">
            <h3>대여 · 구매</h3>
            <div class="provider-grid">
              <a
                v-for="(provider, index) in transactionProviders"
                :key="`txn-${index}-${provider.service}-${provider.type}`"
                class="provider-link"
                :class="{ 'no-link': !hasDeepLink(provider) }"
                :href="resolveProviderHref(provider) || '#'"
                target="_blank"
                rel="noopener noreferrer"
                @click="openProvider($event, provider)"
              >
                <img v-if="provider.icon_url" :src="provider.icon_url" :alt="provider.display_name || provider.service" />
                <span v-else class="provider-fallback">{{ providerInitial(provider.display_name || provider.service) }}</span>
            <strong>{{ provider.display_name || provider.service }}</strong>
            <span>
              {{ provider.type_label }}
              <template v-if="formatLicenseExpiry(provider.expires_on)"> · {{ formatLicenseExpiry(provider.expires_on) }}</template>
              <template v-else-if="!hasDeepLink(provider)"> · 작품 링크 없음</template>
            </span>
              </a>
            </div>
          </div>
        </template>
        <p v-else class="empty">현재 한국에서 이용 가능한 서비스 정보가 없습니다.</p>
      </section>

      <section class="panel" style="margin-top: 18px">
        <h2>출연진</h2>
        <div v-if="movie.cast?.length" class="cast-grid">
          <article v-for="person in movie.cast" :key="`${person.name}-${person.character}`" class="cast-card">
            <img v-if="person.profile_url" :src="person.profile_url" :alt="person.name" loading="lazy" />
            <div v-else class="cast-empty">{{ person.name }}</div>
            <div>
              <strong>{{ person.name }}</strong>
              <span>{{ person.character || '배역 정보 없음' }}</span>
            </div>
          </article>
        </div>
        <p v-else class="empty">출연진 정보가 없습니다.</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(210px, 300px) minmax(0, 1fr);
  gap: 28px;
  align-items: end;
  min-height: 430px;
  margin-top: 18px;
  padding: 28px;
  overflow: hidden;
  border-radius: 8px;
  background: #17202a;
  color: #fff;
}

.detail-hero::before {
  position: absolute;
  inset: 0;
  content: "";
  background-image: linear-gradient(90deg, rgba(17, 24, 32, 0.94), rgba(17, 24, 32, 0.62)), var(--backdrop);
  background-position: center;
  background-size: cover;
}

.detail-poster,
.detail-empty,
.detail-copy {
  position: relative;
  z-index: 1;
}

.detail-poster,
.detail-empty {
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
}

.detail-poster {
  object-fit: cover;
}

.detail-empty {
  display: grid;
  place-items: center;
  background: var(--ws-surface-2);
  color: var(--ws-muted);
  font-weight: 800;
}

.detail-copy {
  display: grid;
  gap: 14px;
}

.detail-copy p {
  max-width: 760px;
  margin: 0;
  color: #e7edf1;
}

.detail-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 13px;
  font-weight: 800;
}

.provider-section + .provider-section {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--ws-border);
}

.provider-section h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--ws-muted);
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.provider-link {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
  cursor: pointer;
}

.provider-link.no-link {
  opacity: 0.72;
}

.provider-link img,
.provider-fallback {
  width: 42px;
  height: 42px;
  border-radius: 8px;
}

.provider-link img {
  object-fit: contain;
}

.provider-fallback {
  display: grid;
  place-items: center;
  background: var(--ws-surface-2);
  color: var(--ws-primary);
  font-weight: 800;
}

.cast-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.cast-card {
  overflow: hidden;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface);
}

.cast-card img,
.cast-empty {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
}

.cast-empty {
  display: grid;
  place-items: center;
  padding: 14px;
  background: var(--ws-surface-2);
  color: var(--ws-muted);
  text-align: center;
  font-weight: 800;
}

.cast-card div:last-child {
  display: grid;
  gap: 4px;
  padding: 11px;
}

.cast-card span {
  overflow: hidden;
  color: var(--ws-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

@media (max-width: 760px) {
  .detail-hero {
    grid-template-columns: 1fr;
    min-height: 0;
    padding: 18px;
  }

  .detail-poster,
  .detail-empty {
    width: min(260px, 100%);
  }
}
</style>
