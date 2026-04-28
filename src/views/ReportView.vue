<template>
  <div class="report">

    <div v-if="report">
      <div class="report-header">
        <div class="header-copy">
          <p class="eyebrow">10-K analysis review</p>
          <h1>{{ report.companyName }} <span class="accent">{{ report.mode === 'verification' ? 'Verification Report' : 'Investor Report' }}</span></h1>
          <p class="fiscal-year">Fiscal Year {{ report.fiscalYear }}</p>
        </div>
      </div>

      <div class="content-wrapper">
        <ReportHero :report="report" />

        <div v-if="report.mode === 'verification'" class="verification-layout">
          <div class="verification-overview">
            <div class="overview-card">
              <span class="overview-label">Documents checked</span>
              <strong>{{ verificationItems.length }}</strong>
            </div>
            <div class="overview-card">
              <span class="overview-label">Verification mode</span>
              <strong>RAG comparison</strong>
            </div>
            <div class="overview-card">
              <span class="overview-label">Report status</span>
              <strong>{{ report.analysis_verification_summary ? 'Ready' : 'Pending' }}</strong>
            </div>
          </div>

          <div class="verification-cards">
            <article
              v-for="item in verificationItems"
              :key="item.file_name"
              class="verification-card"
            >
              <div class="verification-card-header">
                <div>
                  <p class="card-kicker">Uploaded analysis</p>
                  <h2>{{ item.file_name }}</h2>
                </div>
                <span class="status-pill" :class="statusClass(item.overall_status)">{{ formatStatus(item.overall_status) }}</span>
              </div>

              <div class="finding-list">
                <div
                  v-for="finding in item.findings"
                  :key="finding.claim"
                  class="finding-item"
                >
                  <div class="finding-topline">
                    <span class="finding-badge" :class="findingClass(finding.verdict)">{{ finding.verdict }}</span>
                    <p class="finding-claim">{{ finding.claim }}</p>
                  </div>

                  <p class="finding-reason">{{ finding.reason }}</p>

                  <div v-if="finding.evidence" class="evidence-box">
                    <span class="evidence-label">Evidence</span>
                    <p>{{ finding.evidence }}</p>
                  </div>

                  <p v-if="finding.sources?.length" class="finding-sources">
                    Sources: {{ finding.sources.join(', ') }}
                  </p>
                </div>
              </div>
            </article>
          </div>
        </div>

        <div v-else class="sections">
          <ReportSection
            v-for="section in report.sections"
            :key="section.title"
            :section="section"
          />
        </div>
      </div>

      <div class="button-group">
        <button class="download-btn" @click="downloadPDF" v-if="report.pdf_available">📥 Download PDF Report</button>
        <button class="back-btn" @click="router.push('/')">← Verify Another Upload</button>
      </div>
    </div>

    <div v-else class="empty">
      <p>No report found.</p>
      <button class="back-btn" @click="router.push('/')">← Upload a 10-K</button>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ReportHero from '../components/ReportHero.vue'
import ReportSection from '../components/ReportSection.vue'

const report = ref(null)
const jobId = ref(null)
const router = useRouter()
const verificationItems = computed(() => report.value?.analysis_verification || [])

function formatStatus(status) {
  if (status === 'needs_review') return 'Needs review'
  if (status === 'review') return 'Review'
  if (status === 'verified') return 'Verified'
  return 'Unknown'
}

function statusClass(status) {
  if (status === 'needs_review') return 'needs_review'
  if (status === 'review') return 'review'
  if (status === 'verified') return 'verified'
  return 'unknown'
}

function findingClass(verdict) {
  return String(verdict || 'Unclear').toLowerCase().replace(/\s+/g, '-')
}

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
  background:
    radial-gradient(circle at top left, rgba(99, 102, 241, 0.16), transparent 34%),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.12), transparent 28%),
    #0f0f0f;
  color: #ffffff;
  padding: 32px 20px 48px;
}

.report-header {
  max-width: 1180px;
  margin: 0 auto 28px;
  padding: 0 4px;
}

.header-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: #9ca3af;
  font-size: 0.72rem;
}

h1 {
  font-size: clamp(2rem, 3vw, 3.2rem);
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  line-height: 1.1;
}

.accent { color: #6366f1; }

.fiscal-year {
  color: #6b7280;
  font-size: 0.98rem;
  margin: 0;
}

.content-wrapper {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.verification-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.verification-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.overview-card {
  background: rgba(26, 26, 26, 0.92);
  border: 1px solid #2d2d2d;
  border-radius: 16px;
  padding: 18px 18px 16px;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.22);
}

.overview-label {
  display: block;
  color: #9ca3af;
  font-size: 0.82rem;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.overview-card strong {
  font-size: 1.08rem;
  color: #ffffff;
}

.verification-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.verification-card {
  background: rgba(26, 26, 26, 0.96);
  border: 1px solid #2d2d2d;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.2);
}

.verification-card-header {
  display: flex;
  gap: 16px;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.card-kicker {
  margin: 0 0 4px;
  color: #9ca3af;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.verification-card h2 {
  margin: 0;
  font-size: 1.15rem;
  color: #ffffff;
  word-break: break-word;
}

.status-pill,
.finding-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}

.status-pill.verified,
.finding-badge.supported {
  background: rgba(16, 185, 129, 0.18);
  color: #6ee7b7;
}

.status-pill.review,
.finding-badge.partially-supported {
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
}

.status-pill.needs_review,
.finding-badge.unsupported,
.finding-badge.unclear {
  background: rgba(239, 68, 68, 0.18);
  color: #f87171;
}

.finding-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.finding-item {
  border-top: 1px solid #2d2d2d;
  padding-top: 14px;
}

.finding-topline {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.finding-claim {
  margin: 0;
  color: #ffffff;
  line-height: 1.55;
  font-size: 1rem;
}

.finding-reason,
.finding-sources,
.evidence-box p {
  margin: 0;
  color: #d1d5db;
  line-height: 1.7;
  font-size: 0.98rem;
}

.evidence-box {
  margin-top: 10px;
  padding: 12px 14px;
  border-left: 3px solid #6366f1;
  background: rgba(17, 24, 39, 0.85);
  border-radius: 10px;
}

.evidence-label {
  display: block;
  color: #93c5fd;
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.finding-sources {
  margin-top: 10px;
  color: #9ca3af;
  font-size: 0.85rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
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
  margin: 28px auto 0;
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

@media (max-width: 900px) {
  .verification-overview {
    grid-template-columns: 1fr;
  }

  .verification-card-header {
    flex-direction: column;
  }
}
</style>
