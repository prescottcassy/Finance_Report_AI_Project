<template>
  <div class="home">
    <div class="hero">
      <h1>10-K <span class="accent">Verifier</span></h1>
      <p class="subtitle">Upload a 10-K filing and the analysis you want checked against it</p>
    </div>

    <div class="upload-stack">
      <div class="upload-panel">
        <p class="panel-label">1. 10-K filing</p>
        <div class="upload-card" :class="{ dragover: isDraggingTenK }"
          @dragover.prevent="isDraggingTenK = true"
          @dragleave="isDraggingTenK = false"
          @drop.prevent="onTenKDrop"
          @click="tenKInput.click()"
        >
          <input type="file" accept=".pdf" ref="tenKInput" @change="onTenKChange" hidden />

          <div v-if="!tenKFile" class="upload-prompt">
            <div class="upload-icon">↑</div>
            <p>Drag & Drop A 10-K PDF</p>
            <span>or click to upload</span>
          </div>

          <div v-else class="file-selected">
            <div class="upload-icon">✓</div>
            <p>{{ tenKFile.name }}</p>
            <span>Ready for source extraction</span>
          </div>
        </div>
      </div>

      <div class="upload-panel">
        <p class="panel-label">2. Analysis documents</p>
        <div class="upload-card" :class="{ dragover: isDraggingAnalysis }"
          @dragover.prevent="isDraggingAnalysis = true"
          @dragleave="isDraggingAnalysis = false"
          @drop.prevent="onAnalysisDrop"
          @click="analysisInput.click()"
        >
          <input type="file" accept=".pdf,.txt,.md" ref="analysisInput" @change="onAnalysisChange" multiple hidden />

          <div v-if="!analysisFiles.length" class="upload-prompt">
            <div class="upload-icon">⇪</div>
            <p>Drag & Drop Analysis PDFs or text files</p>
            <span>upload one or more documents to verify</span>
          </div>

          <div v-else class="file-selected">
            <div class="upload-icon">✓</div>
            <p>{{ analysisFiles.length }} document{{ analysisFiles.length === 1 ? '' : 's' }} selected</p>
            <span>{{ analysisFiles.map(file => file.name).join(', ') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Company name derived from uploaded 10-K filename; input removed -->

    <LoadingSpinner v-if="isLoading" :message="loadingMessage" :progress="loadingProgress" />
    <button v-else-if="tenKFile" class="analyze-btn" :disabled="!analysisFiles.length" @click="handleUpload">Run Verification</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const router = useRouter()
const tenKInput = ref(null)
const analysisInput = ref(null)
const tenKFile = ref(null)
const analysisFiles = ref([])
// companyName input removed; derive from uploaded file name instead
const isDraggingTenK = ref(false)
const isDraggingAnalysis = ref(false)
const isLoading = ref(false)
const loadingProgress = ref(0)
const loadingMessage = ref('This may take a minute...')

function onTenKChange(e) {
  tenKFile.value = e.target.files[0]
}

function onTenKDrop(e) {
  isDraggingTenK.value = false
  tenKFile.value = e.dataTransfer.files[0]
}

function onAnalysisChange(e) {
  analysisFiles.value = Array.from(e.target.files || [])
}

function onAnalysisDrop(e) {
  isDraggingAnalysis.value = false
  analysisFiles.value = Array.from(e.dataTransfer.files || [])
}

async function handleUpload() {
  if (!tenKFile.value) {
    alert('Please upload a 10-K PDF first.')
    return
  }

  if (!analysisFiles.value.length) {
    alert('Please upload at least one analysis document to verify.')
    return
  }

  isLoading.value = true
  loadingProgress.value = 0
  loadingMessage.value = 'Starting verification...'
  
  const formData = new FormData()
  formData.append('file', tenKFile.value)
  const companyBase = tenKFile.value ? tenKFile.value.name.replace(/\.[^/.]+$/, '') : 'Company'
  formData.append('company', companyBase)
  for (const file of analysisFiles.value) {
    formData.append('analysis_files', file)
  }

  try {
    // Step 1: Submit the file and get job ID
    const submitResponse = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      body: formData
    })
    const submitData = await submitResponse.json()
    
    if (!submitData.job_id) {
      throw new Error(submitData.error || 'Failed to start analysis')
    }

    const jobId = submitData.job_id
    console.log(`Verification started with job ID: ${jobId}`)
    loadingProgress.value = 5
    loadingMessage.value = 'Extracting 10-K source text...'

    // Step 2: Poll for job completion
    let jobComplete = false
    let pollCount = 0
    const maxPolls = 1200 // 20 minutes with 1 second intervals

    while (!jobComplete && pollCount < maxPolls) {
      await new Promise(resolve => setTimeout(resolve, 1000)) // Wait 1 second between polls
      pollCount++

      const statusResponse = await fetch(`http://localhost:8000/job/${jobId}`)
      const statusData = await statusResponse.json()

      // Update progress and message based on status
      if (statusData.status === 'extracting') {
        loadingMessage.value = 'Extracting 10-K sections from PDF...'
      } else if (statusData.status === 'summarizing') {
        loadingMessage.value = 'Building the 10-K evidence corpus...'
      } else if (statusData.status === 'verifying') {
        loadingMessage.value = 'Checking uploaded analysis against the 10-K...'
      }
      
      loadingProgress.value = Math.max(loadingProgress.value, statusData.progress)
      console.log(`Job status: ${statusData.status} (${statusData.progress}%) - ${Math.floor(pollCount / 60)}m ${pollCount % 60}s elapsed`)

      if (statusData.status === 'complete') {
        jobComplete = true
        loadingProgress.value = 100
        localStorage.setItem('report', JSON.stringify(statusData.result))
        localStorage.setItem('jobId', jobId)
        router.push('/report')
      } else if (statusData.status === 'error') {
        throw new Error(statusData.error || 'Analysis failed')
      }
    }

    if (!jobComplete) {
      throw new Error('Analysis timed out after 20 minutes')
    }
  } catch (err) {
    console.error(err)
    alert(`Error: ${err.message}`)
    isLoading.value = false
    loadingProgress.value = 0
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 40px 20px;
  background: #0f0f0f;
}

.hero { text-align: center; }

h1 {
  font-size: 5.5rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px;
}

.accent { color: #6366f1; }

.subtitle {
  color: #9ca3af;
  font-size: 1.5rem;
  max-width: 500px;
  margin: 0 auto;
}

.upload-stack {
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.upload-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-label {
  margin: 0;
  color: #cbd5e1;
  font-size: 0.9rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.upload-card {
  width: 100%;
  border: 2px dashed #2d2d2d;
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  background: #1a1a1a;
  transition: border-color 0.2s, background 0.2s;
}

.upload-card:hover,
.upload-card.dragover {
  border-color: #6366f1;
  background: #1e1e2e;
}

.upload-icon {
  font-size: 2rem;
  margin-bottom: 12px;
  color: #6366f1;
}

.upload-prompt p { color: #ffffff; font-size: 1rem; margin: 0 0 6px; }
.upload-prompt span { color: #6b7280; font-size: 0.875rem; }
.file-selected p { color: #ffffff; font-size: 1rem; margin: 8px 0 4px; }
.file-selected span { color: #6366f1; font-size: 0.875rem; }

/* company input removed */

.analyze-btn {
  padding: 14px 40px;
  background: #6366f1;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.analyze-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.analyze-btn:hover { background: #4f46e5; }
</style>