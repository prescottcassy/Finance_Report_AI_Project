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
    if (file.value) return
        emit('upload', file.value)
    }
</script>