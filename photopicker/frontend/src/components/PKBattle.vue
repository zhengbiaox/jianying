<template>
  <div class="pk-battle">
    <!-- Top actions: only show in multi-photo mode -->
    <div v-if="right && !isSingle" class="pk-top-actions">
      <button class="btn-none" @click="$emit('choose', 'none')">暂缓 ↓</button>
      <button class="btn-both" @click="$emit('choose', 'both')">全部保留 ↑</button>
    </div>

    <div class="pk-sides">
      <!-- Left side (champion / the photo) -->
      <div class="pk-side" :class="{ 'single-photo': isSingle }">
        <img
          v-if="left"
          :src="'/api/preview/' + left.id"
          @click="$emit('zoom', left.id, right ? right.id : null)"
        />
        <div class="pk-info">
          <span class="pk-score">{{ left?.score }} 分</span>
          <div class="pk-exif" v-if="leftExif">
            <span v-if="leftExif.shutter">{{ leftExif.shutter }}</span>
            <span v-if="leftExif.aperture">{{ leftExif.aperture }}</span>
            <span v-if="leftExif.iso">{{ leftExif.iso }}</span>
          </div>
          <span class="pk-name">{{ fileName(left?.path) }}</span>
          <button
            class="pk-btn left"
            @click="$emit('choose', isSingle ? 'keep' : 'left')"
          >
            {{ isSingle ? '✓ 入选' : '← 保留' }}
          </button>
        </div>
      </div>

      <!-- VS / Empty slot divider -->
      <template v-if="!isSingle">
        <div class="pk-vs">VS</div>

        <!-- Right side (challenger) -->
        <div class="pk-side">
          <img
            v-if="right"
            :src="'/api/preview/' + right.id"
            @click="$emit('zoom', left?.id, right.id)"
          />
          <div class="pk-info">
            <span class="pk-score">{{ right?.score }} 分</span>
            <div class="pk-exif" v-if="rightExif">
              <span v-if="rightExif.shutter">{{ rightExif.shutter }}</span>
              <span v-if="rightExif.aperture">{{ rightExif.aperture }}</span>
              <span v-if="rightExif.iso">{{ rightExif.iso }}</span>
            </div>
            <span class="pk-name">{{ fileName(right?.path) }}</span>
            <button class="pk-btn right" @click="$emit('choose', 'right')">
              保留 →
            </button>
          </div>
        </div>
      </template>

      <!-- Single mode: empty slot -->
      <template v-else>
        <div class="pk-vs">—</div>
        <div class="pk-side pk-empty">
          <div class="empty-slot">
            <div class="empty-icon">🚫</div>
            <div class="empty-text">无相似照片</div>
          </div>
          <div class="pk-info">
            <button class="pk-btn reject" @click="$emit('choose', 'reject')">
              ✗ 不要 →
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  left: { type: Object, default: null },
  right: { type: Object, default: null },
  isSingle: { type: Boolean, default: false },
})
defineEmits(['choose', 'zoom'])

const leftExif = ref(null)
const rightExif = ref(null)

function fileName(path) {
  if (!path) return ''
  return path.split('/').pop()
}

async function loadExif() {
  if (props.left?.id) {
    try {
      const res = await axios.get(`/api/exif/${props.left.id}`)
      leftExif.value = res.data
    } catch { leftExif.value = null }
  } else {
    leftExif.value = null
  }
  if (props.right?.id) {
    try {
      const res = await axios.get(`/api/exif/${props.right.id}`)
      rightExif.value = res.data
    } catch { rightExif.value = null }
  } else {
    rightExif.value = null
  }
}

watch(() => [props.left?.id, props.right?.id], loadExif, { immediate: true })
</script>

<style scoped>
.pk-battle { padding: 1rem; }
.pk-top-actions { display: flex; gap: 1rem; justify-content: center; margin-bottom: 1rem; }
.pk-top-actions button { padding: 0.5rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; }
.pk-top-actions .btn-none { background: #333; color: #aaa; }
.pk-top-actions .btn-none:hover { background: #555; color: #fff; }
.pk-top-actions .btn-both { background: #1a5e2a; color: #aaa; }
.pk-top-actions .btn-both:hover { background: #27ae60; color: #fff; }
.pk-sides { display: flex; align-items: center; gap: 1.5rem; }
.pk-side { flex: 1; text-align: center; border: 2px solid transparent; border-radius: 12px; padding: 0.5rem; transition: all 0.2s; }
.pk-side.single-photo { flex: 1; max-width: 55%; }
.pk-side img { width: 100%; max-height: 65vh; object-fit: contain; border-radius: 8px; cursor: pointer; }
.pk-info { margin-top: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }
.pk-score { color: #aaa; font-size: 0.85rem; }
.pk-exif { display: flex; gap: 0.8rem; color: #666; font-size: 0.8rem; }
.pk-name { color: #666; font-size: 0.75rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pk-btn { padding: 0.5rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.2s; }
.pk-btn.left { background: #e74c3c; color: #fff; }
.pk-btn.right { background: #3498db; color: #fff; }
.pk-btn.reject { background: #555; color: #fff; }
.pk-btn:hover { opacity: 0.8; transform: scale(1.02); }
.pk-vs { font-size: 1.5rem; color: #555; font-weight: bold; min-width: 40px; text-align: center; }

/* Empty slot styling */
.pk-empty { border: 2px dashed #333; }
.empty-slot { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; color: #555; }
.empty-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.empty-text { font-size: 1rem; color: #666; }
</style>
