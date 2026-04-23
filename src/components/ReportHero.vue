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