<template>
  <div class="report-hero">
    <h1>{{ report.companyName }}</h1>
    <p class="fiscal-year">Fiscal Year {{ report.fiscalYear }}</p>

    <div v-if="report.verification_summary" class="bluf">
      <h2>Verification Summary</h2>
      <p class="summary-text">{{ report.verification_summary }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  report: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.report-hero {
  background: rgba(26, 26, 26, 0.96);
  border-radius: 18px;
  padding: 28px 24px;
  border: 1px solid #2d2d2d;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.2);
}

h1 {
  font-size: 2.2rem;
  font-weight: 600;
  margin: 0 0 8px;
}

.fiscal-year {
  color: #6b7280;
  font-size: 1rem;
  margin: 0 0 24px;
}

.bluf,
.narrative {
  margin: 18px 0 0;
}

h2 {
  font-size: 1.4rem;
  font-weight: 500;
  color: #6366f1;
  margin: 0 0 12px;
}

.summary-text {
  color: #d1d5db;
  line-height: 1.8;
  margin: 0;
  font-size: 1rem;
  white-space: pre-wrap;
}
</style>