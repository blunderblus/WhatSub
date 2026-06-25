<script setup>
import PageHeader from '../components/PageHeader.vue';
import UserSubscriptionDashboard from '../components/UserSubscriptionDashboard.vue';
</script>

<template>
  <main class="ws-page">
    <PageHeader eyebrow="My Subscriptions" title="내 구독 대시보드" />
    <UserSubscriptionDashboard />
  </main>
</template>
