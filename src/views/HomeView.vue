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
        <p>Drag & drop your 10-K PDF</p>
        <span>or click to browse</span>
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

    <LoadingSpinner v-if="isLoading" message="This may take a minute..." />
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

function onFileChange(e) {
  file.value = e.target.files[0]
}

function onDrop(e) {
  isDragging.value = false
  file.value = e.dataTransfer.files[0]
}

function handleUpload() {
  isLoading.value = true
  setTimeout(() => {
    router.push('/report')
    isLoading.value = false
  }, 2000)
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
  font-size: 2.5rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px;
}

.accent { color: #6366f1; }

.subtitle {
  color: #9ca3af;
  font-size: 1rem;
  max-width: 400px;
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