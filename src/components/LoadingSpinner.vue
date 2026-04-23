<template>
  <div class="spinner-wrapper">
    <div class="spinner"></div>
    <p>{{ message }}</p>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }"></div>
    </div>
    <p class="progress-text">{{ progress }}%</p>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: String,
    default: 'Analyzing your 10-K...'
  },
  progress: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.spinner-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 5px solid #e0e0e0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

p {
  color: #6b7280;
  font-size: 0.95rem;
}

.progress-bar {
  width: 200px;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.85rem;
  margin: 0 !important;
}
</style>