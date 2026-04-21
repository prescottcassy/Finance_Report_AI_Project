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
</template>