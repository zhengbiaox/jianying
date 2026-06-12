<template>
  <div class="zoom-viewer" v-if="visible" @click.self="$emit('close')">
    <div class="zoom-content">
      <img :src="src" ref="imgRef" @load="onLoad" />
    </div>
    <button class="close-btn" @click="$emit('close')">✕</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  src: { type: String, required: true },
  visible: { type: Boolean, default: false }
})
defineEmits(['close'])

const imgRef = ref(null)

function onLoad() {
  if (imgRef.value) {
    imgRef.value.style.transform = 'scale(2)'
  }
}
</script>

<style scoped>
.zoom-viewer { position: fixed; inset: 0; background: rgba(0,0,0,0.95); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.zoom-content { max-width: 90vw; max-height: 90vh; overflow: hidden; }
.zoom-content img { max-width: 90vw; max-height: 90vh; object-fit: contain; transition: transform 0.3s; transform-origin: center center; }
.close-btn { position: fixed; top: 1rem; right: 1rem; background: none; border: none; color: #fff; font-size: 2rem; cursor: pointer; }
</style>
