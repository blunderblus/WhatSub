import { onBeforeUnmount, ref } from 'vue';

export function useTimedCarousel(itemCount, { intervalMs = 5000 } = {}) {
  const activeIndex = ref(0);
  const timer = ref(null);

  function select(index) {
    const count = Number(itemCount || 0);
    if (count <= 0) {
      activeIndex.value = 0;
      return;
    }
    activeIndex.value = ((index % count) + count) % count;
  }

  function start() {
    if (timer.value || itemCount <= 1) return;
    timer.value = setInterval(() => {
      select(activeIndex.value + 1);
    }, intervalMs);
  }

  function stop() {
    if (!timer.value) return;
    clearInterval(timer.value);
    timer.value = null;
  }

  onBeforeUnmount(stop);

  return {
    activeIndex,
    select,
    start,
    stop,
  };
}
