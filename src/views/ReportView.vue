<template>
  <div class="report">

    <div v-if="report">
      <div class="report-header">
        <h1>{{ report.companyName }} <span class="accent">Investor Report</span></h1>
        <p class="fiscal-year">Fiscal Year {{ report.fiscalYear }}</p>
      </div>

      <ReportHero :report="report" />

      <div class="sections">
        <ReportSection
          v-for="section in report.sections"
          :key="section.title"
          :section="section"
        />
      </div>

      <button class="back-btn" @click="router.push('/')">← Analyze Another</button>
    </div>

    <div v-else class="empty">
      <p>No report found.</p>
      <button class="back-btn" @click="router.push('/')">← Upload a 10-K</button>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ReportHero from '../components/ReportHero.vue'
import ReportSection from '../components/ReportSection.vue'

const report = ref(null)
const router = useRouter()

onMounted(() => {
  const stored = localStorage.getItem('report')
  if (stored) report.value = JSON.parse(stored)
})
</script>

<style scoped>
.report {
  min-height: 100vh;
  background: #0f0f0f;
  color: #ffffff;
  padding: 40px 20px;
}

.report-header {
  text-align: center;
  margin-bottom: 40px;
}

h1 {
  font-size: 2rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px;
}

.accent { color: #6366f1; }

.fiscal-year {
  color: #6b7280;
  font-size: 0.95rem;
  margin: 0;
}

.sections {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.back-btn {
  display: block;
  margin: 40px auto 0;
  padding: 12px 32px;
  background: transparent;
  color: #6366f1;
  border: 1px solid #6366f1;
  border-radius: 10px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.back-btn:hover {
  background: #6366f1;
  color: #ffffff;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 20px;
  color: #9ca3af;
}
</style>