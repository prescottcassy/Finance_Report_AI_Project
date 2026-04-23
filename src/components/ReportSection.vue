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