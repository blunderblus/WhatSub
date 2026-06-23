<script setup>
import {
  billingLabel,
  buildCalcItemFromAddon,
  buildCalcItemFromPlan,
  formatWon,
  parsePromoNotes,
  planMonthlyPrice,
} from '../utils/billing';

const props = defineProps({
  catalog: {
    type: Object,
    default: () => ({}),
  },
  loading: {
    type: Boolean,
    default: false,
  },
  platformName: {
    type: String,
    default: '',
  },
  readonly: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['add-item']);

const hasAny = () =>
  (props.catalog.plans?.length || 0)
  + (props.catalog.bundles?.length || 0)
  + (props.catalog.related_bundles?.length || 0)
  + (props.catalog.addon_passes?.length || 0) > 0;

function onDragStart(event, payload) {
  event.dataTransfer.setData('application/json', JSON.stringify(payload));
  event.dataTransfer.effectAllowed = 'copy';
}

function addPlan(plan, itemType = 'plan') {
  emit('add-item', buildCalcItemFromPlan(plan, itemType));
}

function addAddon(passItem, pricing) {
  emit('add-item', buildCalcItemFromAddon(passItem, pricing, props.platformName));
}

function bundlePlatforms(plan) {
  return (plan.bundle_contents || []).map((b) => b.included_platform_name).join(' + ');
}
</script>

<template>
  <div class="catalog">
    <div v-if="loading" class="muted small">요금·번들·프로모션 불러오는 중...</div>
    <div v-else-if="!hasAny()" class="muted small">등록된 요금제가 없습니다.</div>

    <template v-else>
      <section v-if="catalog.plans?.length" class="catalog-section">
        <h4>일반 요금제</h4>
        <div class="plan-grid">
          <component
            :is="readonly ? 'div' : 'button'"
            v-for="plan in catalog.plans"
            :key="`plan-${plan.id}`"
            type="button"
            class="plan-card"
            :draggable="!readonly"
            @dragstart="!readonly && onDragStart($event, buildCalcItemFromPlan(plan, 'plan'))"
            @click="!readonly && addPlan(plan, 'plan')"
          >
            <strong>{{ plan.plan_name }}</strong>
            <span>{{ formatWon(plan.price) }}원 · {{ billingLabel(plan.billing_period) }}</span>
            <span>월 {{ formatWon(planMonthlyPrice(plan)) }}원 환산</span>
            <span v-if="plan.max_quality">{{ plan.max_quality }} · 동시 {{ plan.max_streams }}</span>
            <ul v-if="parsePromoNotes(plan.notes).length" class="promo-list">
              <li v-for="(promo, i) in parsePromoNotes(plan.notes)" :key="i">{{ promo }}</li>
            </ul>
          </component>
        </div>
      </section>

      <section v-if="catalog.bundles?.length" class="catalog-section">
        <h4>번들 상품</h4>
        <div class="plan-grid">
          <component
            :is="readonly ? 'div' : 'button'"
            v-for="plan in catalog.bundles"
            :key="`bundle-${plan.id}`"
            type="button"
            class="plan-card"
            :draggable="!readonly"
            @dragstart="!readonly && onDragStart($event, buildCalcItemFromPlan(plan, 'bundle'))"
            @click="!readonly && addPlan(plan, 'bundle')"
          >
            <span class="badge">번들</span>
            <strong>{{ plan.plan_name }}</strong>
            <span v-if="bundlePlatforms(plan)" class="bundle-platforms">{{ bundlePlatforms(plan) }}</span>
            <span>{{ formatWon(plan.price) }}원 · {{ billingLabel(plan.billing_period) }}</span>
            <span>월 {{ formatWon(planMonthlyPrice(plan)) }}원 환산</span>
            <ul v-if="parsePromoNotes(plan.notes).length" class="promo-list">
              <li v-for="(promo, i) in parsePromoNotes(plan.notes)" :key="i">{{ promo }}</li>
            </ul>
          </component>
        </div>
      </section>

      <section v-if="catalog.related_bundles?.length" class="catalog-section">
        <h4>제휴·크로스 번들</h4>
        <p class="section-note">다른 플랫폼과 묶인 번들 상품입니다.</p>
        <div class="plan-grid">
          <component
            :is="readonly ? 'div' : 'button'"
            v-for="plan in catalog.related_bundles"
            :key="`rel-${plan.id}`"
            type="button"
            class="plan-card cross-bundle"
            :draggable="!readonly"
            @dragstart="!readonly && onDragStart($event, buildCalcItemFromPlan(plan, 'related_bundle'))"
            @click="!readonly && addPlan(plan, 'related_bundle')"
          >
            <span class="badge cross">제휴</span>
            <strong>{{ plan.platform_name }} · {{ plan.plan_name }}</strong>
            <span v-if="bundlePlatforms(plan)" class="bundle-platforms">{{ bundlePlatforms(plan) }}</span>
            <span>{{ formatWon(plan.price) }}원 · {{ billingLabel(plan.billing_period) }}</span>
            <span>월 {{ formatWon(planMonthlyPrice(plan)) }}원 환산</span>
          </component>
        </div>
      </section>

      <section v-if="catalog.addon_passes?.length" class="catalog-section">
        <h4>애드온·프로모션 패스</h4>
        <div v-for="passItem in catalog.addon_passes" :key="passItem.id" class="addon-block">
          <h5>{{ passItem.pass_name }}</h5>
          <div class="plan-grid">
            <component
              :is="readonly ? 'div' : 'button'"
              v-for="pricing in passItem.pricings"
              :key="pricing.id"
              type="button"
              class="plan-card"
              :draggable="!readonly"
              @dragstart="!readonly && onDragStart($event, buildCalcItemFromAddon(passItem, pricing, platformName))"
              @click="!readonly && addAddon(passItem, pricing)"
            >
              <span class="badge addon-badge">패스</span>
              <strong>{{ pricing.base_plan_name || '기본 요금제 연동' }}</strong>
              <span>{{ formatWon(pricing.price) }}원 · {{ billingLabel(pricing.billing_period) }}</span>
              <span>월 {{ formatWon(planMonthlyPrice(pricing)) }}원 환산</span>
            </component>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.catalog-section {
  margin-top: 16px;
}

.catalog-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.catalog-section h5 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--ws-muted);
}

.section-note {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--ws-muted);
}

.addon-block + .addon-block {
  margin-top: 12px;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.plan-card {
  position: relative;
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid #c6f349;
  border-radius: 10px;
  background: #141414;
  color: #ffffff;
  text-align: left;
  font-size: 13px;
}

.plan-card strong,
.plan-card span,
.plan-card .bundle-platforms {
  color: #ffffff;
}

button.plan-card {
  cursor: grab;
}

button.plan-card:active {
  cursor: grabbing;
}

.plan-card strong {
  font-size: 14px;
}

.plan-card.cross-bundle {
  border-color: #57534e;
  background: #1c1917;
  color: #fafaf9;
}

.plan-card.cross-bundle strong {
  color: #fafaf9;
}

.plan-card.cross-bundle .bundle-platforms,
.plan-card.cross-bundle span:not(.badge) {
  color: #e7e5e4;
}

.badge {
  align-self: start;
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: #c6f349;
  color: #141414;
  font-size: 11px;
  font-weight: 800;
}

.badge.cross {
  background: #fbbf24;
  color: #78350f;
}

.badge.addon-badge {
  background: #c6f349;
  color: #141414;
}

.bundle-platforms {
  font-size: 12px;
}

.promo-list {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: 11px;
  color: #c6f349;
}

.promo-list li {
  color: #c6f349;
}
</style>
