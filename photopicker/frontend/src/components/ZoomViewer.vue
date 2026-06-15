<template>
  <div class="zoom-overlay" v-if="visible" @click.self="close">
    <div class="zoom-container">
      <div class="zoom-side" v-if="leftSrc">
        <div class="zoom-viewport" ref="leftViewport"
             @wheel.prevent="onWheel"
             @mousedown="onMouseDown"
             @mousemove="onMouseMove"
             @mouseup="onMouseUp"
             @mouseleave="onMouseUp">
          <img :src="leftSrc" :style="transformStyle" draggable="false" />
        </div>
        <div class="zoom-label">左侧</div>
      </div>
      <div class="zoom-side" v-if="rightSrc">
        <div class="zoom-viewport" ref="rightViewport"
             @wheel.prevent="onWheel"
             @mousedown="onMouseDown"
             @mousemove="onMouseMove"
             @mouseup="onMouseUp"
             @mouseleave="onMouseUp">
          <img :src="rightSrc" :style="transformStyle" draggable="false" />
        </div>
        <div class="zoom-label">右侧</div>
      </div>
    </div>
    <div class="zoom-controls">
      <button @click="zoomIn">放大 (+)</button>
      <button @click="zoomOut">缩小 (-)</button>
      <button @click="resetTransform">重置</button>
      <span class="zoom-level">{{ zoomLevel }}x</span>
      <button @click="close" class="zoom-close">关闭 (Esc)</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  leftSrc: { type: String, default: '' },
  rightSrc: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartTX = ref(0)
const dragStartTY = ref(0)

const ZOOM_LEVELS = [1, 2, 4]
const zoomLevel = computed(() => {
  const closest = ZOOM_LEVELS.reduce((prev, curr) =>
    Math.abs(curr - scale.value) < Math.abs(prev - scale.value) ? curr : prev
  )
  return closest
})

const transformStyle = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  transformOrigin: 'center center',
  transition: isDragging.value ? 'none' : 'transform 0.2s ease-out',
}))

function zoomIn() {
  const idx = ZOOM_LEVELS.indexOf(zoomLevel.value)
  if (idx < ZOOM_LEVELS.length - 1) {
    scale.value = ZOOM_LEVELS[idx + 1]
  }
}

function zoomOut() {
  const idx = ZOOM_LEVELS.indexOf(zoomLevel.value)
  if (idx > 0) {
    scale.value = ZOOM_LEVELS[idx - 1]
    if (scale.value === 1) {
      translateX.value = 0
      translateY.value = 0
    }
  }
}

function resetTransform() {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
}

function onWheel(e) {
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

function onMouseDown(e) {
  if (e.button !== 0) return
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY
  dragStartTX.value = translateX.value
  dragStartTY.value = translateY.value
}

function onMouseMove(e) {
  if (!isDragging.value) return
  translateX.value = dragStartTX.value + (e.clientX - dragStartX.value)
  translateY.value = dragStartTY.value + (e.clientY - dragStartY.value)
}

function onMouseUp() {
  isDragging.value = false
}

function onKeyDown(e) {
  if (!props.visible) return
  if (e.key === 'Escape') close()
  if (e.key === 'z' || e.key === 'Z') {
    if (e.shiftKey) return
    const idx = ZOOM_LEVELS.indexOf(zoomLevel.value)
    scale.value = ZOOM_LEVELS[(idx + 1) % ZOOM_LEVELS.length]
    if (scale.value === 1) { translateX.value = 0; translateY.value = 0 }
  }
  if (e.key === '+' || e.key === '=') zoomIn()
  if (e.key === '-') zoomOut()
}

function close() {
  resetTransform()
  emit('close')
}

watch(() => props.visible, (v) => {
  if (v) {
    resetTransform()
    document.addEventListener('keydown', onKeyDown)
  } else {
    document.removeEventListener('keydown', onKeyDown)
  }
})

onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<style scoped>
.zoom-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.95); z-index: 1000;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.zoom-container {
  display: flex; gap: 4px; width: 95vw; height: 80vh;
}
.zoom-side {
  flex: 1; position: relative; overflow: hidden; border-radius: 8px; background: #111;
}
.zoom-viewport {
  width: 100%; height: 100%; overflow: hidden; cursor: grab;
  display: flex; align-items: center; justify-content: center;
}
.zoom-viewport:active { cursor: grabbing; }
.zoom-viewport img {
  max-width: 100%; max-height: 100%; object-fit: contain; user-select: none;
}
.zoom-label {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  background: rgba(0,0,0,0.6); color: #aaa; padding: 2px 12px; border-radius: 4px;
  font-size: 0.85rem;
}
.zoom-controls {
  display: flex; gap: 0.5rem; align-items: center; margin-top: 1rem;
}
.zoom-controls button {
  padding: 0.4rem 1rem; background: #333; color: #ccc; border: none;
  border-radius: 6px; cursor: pointer; font-size: 0.9rem;
}
.zoom-controls button:hover { background: #444; color: #fff; }
.zoom-level { color: #888; font-size: 0.9rem; min-width: 3rem; text-align: center; }
.zoom-close { background: #c0392b !important; }
</style>
