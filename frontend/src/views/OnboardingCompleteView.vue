<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

const canvasRef = ref(null);
let animationId = null;
let resizeHandler = null;

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let W = 0;
  let H = 0;
  const colors = ['#2f6f73', '#e50914', '#01137c', '#00a8e1', '#f5c518', '#ff6b6b', '#4ecdc4'];
  const pieces = [];

  resizeHandler = () => {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  };
  resizeHandler();

  for (let i = 0; i < 120; i += 1) {
    pieces.push({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight - window.innerHeight,
      w: 6 + Math.random() * 8,
      h: 10 + Math.random() * 6,
      color: colors[i % colors.length],
      vy: 2 + Math.random() * 3,
      vx: -1 + Math.random() * 2,
      rot: Math.random() * 360,
      vr: -4 + Math.random() * 8,
    });
  }

  function frame() {
    ctx.clearRect(0, 0, W, H);
    pieces.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      if (p.y > H + 20) {
        p.y = -20;
        p.x = Math.random() * W;
      }
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rot * Math.PI) / 180);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });
    animationId = requestAnimationFrame(frame);
  }

  window.addEventListener('resize', resizeHandler);
  frame();
});

onUnmounted(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler);
  if (animationId) cancelAnimationFrame(animationId);
});
</script>

<template>
  <canvas ref="canvasRef" class="confetti" />
  <main class="card">
    <h1>WhatSub?에 오신 것을 환영합니다!</h1>
    <h2>함께 슬기로운 구독생활 해봐요.</h2>
    <p class="note">
      분석에 사용된 이메일 내용은 서버에 저장되지 않았으며, 스캔이 끝난 뒤 자동으로 폐기되었습니다.
    </p>
    <RouterLink class="button primary" to="/subscriptions">내 대시보드로 이동</RouterLink>
  </main>
</template>

<style scoped>
.confetti {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 10;
}

.card {
  position: relative;
  z-index: 20;
  width: min(520px, calc(100% - 32px));
  margin: 12vh auto 0;
  padding: 48px 36px;
  text-align: center;
  border: 1px solid #dce3e9;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 24px 64px rgba(27, 39, 51, 0.12);
  animation: pop 0.6s cubic-bezier(0.2, 1.2, 0.3, 1) both;
}

@keyframes pop {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

h1 {
  margin: 0 0 12px;
  font-size: 32px;
  color: #111820;
}

h2 {
  margin: 0 0 24px;
  font-size: 18px;
  font-weight: 600;
  color: #687785;
}

.note {
  margin: 0 0 28px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #eef6f6;
  color: #45525e;
  font-size: 13px;
  line-height: 1.5;
}
</style>
