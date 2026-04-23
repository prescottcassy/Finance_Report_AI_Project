<template>
    <div 
        class="uploader"
        @dragover.prevent
        @drop.prevent="onDrop"
    >
        <input
            type="file"
            accept=".pdf"
            ref="fileInput"
            @change="onFileChange"
            hidden
        />
        <div @click="fileInput.click()">
            <p v-if="!fileName">Click or drag a 10k PDF file here </p>
            <p v-else>{{ fileName }}</p>
        </div>

        <button :disabled="!file" @click="submit">Extract Important Information</button>
    </div>
</template>
<script setup>
import { ref } from 'vue'
const emit = defineEmits(['file-uploaded'])
const fileInput = ref(null)
const file = ref(null)

function onFileChange(e) {
    file.value = e.target.files[0]
}

function onDrop(e) {
    file.value = e.dataTransfer.files[0]
}

function submit() {
  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('company', companyName.value)
  emit('upload', formData)
}
</script>

<style scoped>
.uploader {
  border: 2px dashed #2d2d2d;
  border-radius: 10px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
}

.uploader:hover {
  border-color: #6366f1;
  background: #1a1a1a;
}

p {
  color: #9ca3af;
  margin: 8px 0;
}

button {
  margin-top: 16px;
  padding: 10px 24px;
  background: #6366f1;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

button:disabled {
  background: #4b5563;
  cursor: not-allowed;
}
</style>