<template>
  <div class="home">
    <div class="hero">
      <h1>10-K <span class="accent">Investor Report</span></h1>
      <p class="subtitle">Upload a 10-K filing and get an AI-generated investor-ready report in minutes</p>
    </div>

    <div class="upload-card" :class="{ dragover: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <input type="file" accept=".pdf" ref="fileInput" @change="onFileChange" hidden />

      <div v-if="!file" class="upload-prompt">
        <div class="upload-icon">↑</div>
        <p>Drag & Drop A 10-K PDF</p>
        <span>or click to upload</span>
      </div>

      <div v-else class="file-selected">
        <div class="upload-icon">✓</div>
        <p>{{ file.name }}</p>
        <span>Ready to analyze</span>
      </div>

    </div>

    <div v-if="file" class="company-input">
      <input v-model="companyName" type="text" placeholder="Company name (e.g. Qualcomm)" />
    </div>

    <LoadingSpinner v-if="isLoading" :message="loadingMessage" :progress="loadingProgress" />
    <button v-else-if="file" class="analyze-btn" @click="handleUpload">Generate Report</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const router = useRouter()
const fileInput = ref(null)
const file = ref(null)
const companyName = ref('')
const isDragging = ref(false)
const isLoading = ref(false)
const loadingProgress = ref(0)
const loadingMessage = ref('This may take a minute...')

function onFileChange(e) {
  file.value = e.target.files[0]
}

function onDrop(e) {
  isDragging.value = false
  file.value = e.dataTransfer.files[0]
}

async function handleUpload() {
  isLoading.value = true
  loadingProgress.value = 0
  loadingMessage.value = 'Starting analysis...'
  
  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('company', companyName.value || 'Company')

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
    console.log(`Analysis started with job ID: ${jobId}`)
    loadingProgress.value = 5
    loadingMessage.value = 'Extracting 10-K sections...'

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
        loadingMessage.value = 'Generating AI summaries (this takes time)...'
      } else if (statusData.status === 'generating') {
        loadingMessage.value = 'Creating investor narrative...'
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

.upload-card {
  width: 100%;
  max-width: 480px;
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

.company-input input {
  width: 100%;
  max-width: 480px;
  padding: 12px 16px;
  background: #1a1a1a;
  border: 1px solid #2d2d2d;
  border-radius: 10px;
  color: #ffffff;
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
}

.company-input input:focus { border-color: #6366f1; }

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

.analyze-btn:hover { background: #4f46e5; }
</style>