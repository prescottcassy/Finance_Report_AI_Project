<template>
  <div class="report-view">
    <ReportHero :report="report" />
    <ReportSection 
      v-for="section in report.sections"
      :key="section.title"
      :section="section"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ReportHero from '../components/ReportHero.vue'
import ReportSection from '../components/ReportSection.vue'

const report = ref({
  title: 'Financial Report',
  sections: []
})

onMounted(() => {
  // Load report data here
})
</script>

<style scoped>
.report-view {
  padding: 20px;
}
</style>