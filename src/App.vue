<template>
  <div id="app">
    <h1>Finance Report AI Project</h1>
    <FileUploader @file-uploaded="handleFileUpload" />
  </div>
</template>

<script setup>
import FileUploader from './components/FileUploader.vue'

function handleFileUpload(file) {
  console.log('File uploaded:', file)
}
</script>

<style scoped>
h1 {
  text-align: center;
  margin: 20px 0;
}
</style>
