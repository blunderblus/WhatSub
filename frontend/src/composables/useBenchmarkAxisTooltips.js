import { onBeforeUnmount, onMounted, ref } from 'vue';

const AXIS_TOOLTIPS = {
  availability: '이 플랫폼에서 볼 수 있는 영화·시리즈가 얼마나 많은지를 나타내요. 다른 플랫폼들과 비교한 상대적 점수예요.',
  exclusivity: '오직 이 플랫폼에서만 볼 수 있는 작품이 얼마나 있는지, 그리고 그 작품들이 얼마나 화제성 있는지를 함께 반영해요.',
  quality: '평점 높은 좋은 작품이 얼마나 많은지를 나타내요. 평가 안 좋은 작품이 많다고 해서 점수가 깎이지는 않아요.',
  price: '합리적인 가격의 플랜이나 번들 혜택이 얼마나 있는지를 나타내요. 가격 대비 실질적인 혜택을 기준으로 판단해요.',
  accessibility: '동시 시청 가능 인원, 최대 화질, 다운로드 지원 여부 등 실제 이용 편의성을 나타내요.',
};

export function useBenchmarkAxisTooltips() {
  const activeTooltip = ref(null);

  function toggleTooltip(key) {
    activeTooltip.value = activeTooltip.value === key ? null : key;
  }

  function closeTooltip() {
    activeTooltip.value = null;
  }

  onMounted(() => {
    document.addEventListener('click', closeTooltip);
  });

  onBeforeUnmount(() => {
    document.removeEventListener('click', closeTooltip);
  });

  return {
    activeTooltip,
    axisTooltips: AXIS_TOOLTIPS,
    toggleTooltip,
  };
}
