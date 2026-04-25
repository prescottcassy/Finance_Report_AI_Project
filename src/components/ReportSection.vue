<template>
  <div class="report-section">
    <div class="section-header" @click="toggle">
      <h3>{{ section.title }}</h3>
      <span>{{ isOpen ? '▲' : '▼' }}</span>
    </div>

    <div v-if="isOpen" class="section-body">
      <p>{{ section.summary }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  section: {
    type: Object,
    required: true
  }
})

const isOpen = ref(false)

function toggle() {
  isOpen.value = !isOpen.value
}
</script>

<style scoped>
.report-section {
  background: #1a1a1a;
  border: 1px solid #2d2d2d;
  border-radius: 10px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.section-header:hover {
  background: #242424;
}

h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 500;
  color: #ffffff;
}

span {
  color: #6366f1;
  font-size: 0.9rem;
}

.section-body {
  padding: 16px 20px;
  border-top: 1px solid #2d2d2d;
  background: #0f0f0f;
}

p {
  margin: 0;
  color: #d1d5db;
  line-height: 1.8;
  font-size: 1.05rem;
}
</style>