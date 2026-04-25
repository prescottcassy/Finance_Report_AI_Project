<template>
  <div class="report-hero">
    <h1>{{ report.companyName }}</h1>
    <p class="fiscal-year">Fiscal Year {{ report.fiscalYear }}</p>

    <!-- BLUF -->
    <div class="bluf">
      <h2>Bottom Line</h2>
      <p>{{ report.bluf }}</p>
    </div>

    <!-- Narrative -->
    <div class="narrative">
      <h2>The Story</h2>
      <p>{{ report.narrative }}</p>
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
  background: #1a1a1a;
  border-radius: 12px;
  padding: 32px 24px;
  margin-bottom: 24px;
  border: 1px solid #2d2d2d;
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
  margin: 24px 0;
}

h2 {
  font-size: 1.4rem;
  font-weight: 500;
  color: #6366f1;
  margin: 0 0 12px;
}

p {
  color: #d1d5db;
  line-height: 1.8;
  margin: 0;
  font-size: 1.05rem;
}
</style>