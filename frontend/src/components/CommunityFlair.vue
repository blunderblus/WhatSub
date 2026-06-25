<script setup>
import { computed } from 'vue';
import {
  flairStyle,
  flairTheme,
  FLAIR_NONE_THEME,
  flairDisplayLabel,
  flairFullLabel,
} from '../utils/platformFlair';

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  platformName: {
    type: String,
    default: '',
  },
  flairTag: {
    type: String,
    default: '',
  },
  isNotice: {
    type: Boolean,
    default: false,
  },
  selected: {
    type: Boolean,
    default: false,
  },
  selectable: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['select']);

const flairProps = computed(() => ({
  platformName: props.platformName,
  flairTag: props.flairTag,
  isNotice: props.isNotice,
  label: props.label,
}));

const displayLabel = computed(() => flairDisplayLabel({
  ...flairProps.value,
  compact: props.compact,
}));

const tooltipLabel = computed(() => flairFullLabel(flairProps.value));

const theme = computed(() => {
  if (!props.platformName && !props.flairTag && !props.isNotice && props.label) {
    return FLAIR_NONE_THEME;
  }
  return flairTheme({
    platformName: props.platformName || props.label,
    flairTag: props.flairTag,
    isNotice: props.isNotice,
  });
});

const hasFlair = computed(() => Boolean(displayLabel.value && theme.value));

function onClick() {
  if (props.selectable) emit('select');
}
</script>

<template>
  <span
    v-if="hasFlair"
    class="community-flair"
    :class="{ selected, selectable, compact }"
    :style="flairStyle(theme)"
    :title="compact && tooltipLabel !== displayLabel ? tooltipLabel : undefined"
    :role="selectable ? 'button' : undefined"
    :tabindex="selectable ? 0 : undefined"
    @click="onClick"
    @keydown.enter.prevent="onClick"
  >
    <span class="flair-label">{{ displayLabel }}</span>
  </span>
</template>

<style scoped>
.community-flair {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  min-width: 0;
  min-height: 26px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--flair-ring);
  background: var(--flair-bg);
  color: var(--flair-text);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.01em;
  vertical-align: middle;
}

.flair-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.community-flair.compact {
  min-height: 22px;
  padding: 2px 8px;
  font-size: 10px;
  line-height: 1.1;
}

.community-flair.selectable {
  cursor: pointer;
  transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
}

.community-flair.selectable:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
}

.community-flair.selectable.selected {
  box-shadow: 0 0 0 2px var(--flair-ring), 0 8px 18px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}
</style>
