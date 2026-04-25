<template>
  <div class="report">

    <div v-if="report">
      <div class="report-header">
        <h1>{{ report.companyName }} <span class="accent">Investor Report</span></h1>
        <p class="fiscal-year">Fiscal Year {{ report.fiscalYear }}</p>
      </div>

      <div class="content-wrapper">
        <ReportHero :report="report" />

        <div class="sections">
          <ReportSection
            v-for="section in report.sections"
            :key="section.title"
            :section="section"
          />
        </div>
      </div>

      <div class="button-group">
        <button class="download-btn" @click="downloadPDF" v-if="report.pdf_available">📥 Download PDF Report</button>
        <button class="back-btn" @click="router.push('/')">← Analyze Another</button>
      </div>
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
const jobId = ref(null)
const router = useRouter()

onMounted(() => {
  const stored = localStorage.getItem('report')
  const storedJobId = localStorage.getItem('jobId')
  if (stored) report.value = JSON.parse(stored)
  if (storedJobId) jobId.value = storedJobId
})

async function downloadPDF() {
  if (!jobId.value) {
    alert('No job ID found for this report')
    return
  }
  
  try {
    const response = await fetch(`http://localhost:8000/download/${jobId.value}`)
    if (!response.ok) {
      throw new Error('Failed to download PDF')
    }
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.value?.companyName || 'report'}_10k_analysis.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (err) {
    console.error('Download error:', err)
    alert('Failed to download PDF')
  }
}
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
  font-size: 2.5rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px;
}

.accent { color: #6366f1; }

.fiscal-year {
  color: #6b7280;
  font-size: 1.05rem;
  margin: 0;
}

.content-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 5rem;
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

.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 40px;
  flex-wrap: wrap;
}

.download-btn {
  padding: 12px 32px;
  background: #10b981;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s;
  font-weight: 500;
}

.download-btn:hover {
  background: #059669;
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