<template>
  <div class="confirm-view">
    <h2>最终确认</h2>
    <p>以下是你选出的照片，确认无误后导出</p>

    <div class="confirm-stats">
      <span>胜出: <strong>{{ winners.length }}</strong> 张</span>
      <span>淘汰: <strong>{{ losersCount }}</strong> 张</span>
    </div>

    <div class="confirm-grid">
      <div v-for="photo in winners" :key="photo.id" class="confirm-card">
        <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
        <span class="card-score">{{ photo.score }}</span>
      </div>
    </div>

    <div class="confirm-actions">
      <div class="mode-select">
        <label>导出模式:</label>
        <label><input type="radio" v-model="mode" value="copy" /> 复制</label>
        <label><input type="radio" v-model="mode" value="move" /> 移动</label>
      </div>
      <button class="export-btn" @click="doExport" :disabled="exporting">
        {{ exporting ? '导出中...' : '确认导出' }}
      </button>
    </div>

    <div v-if="exportResult" class="export-result">
      <p>✅ 导出完成！</p>
      <p>胜出: {{ exportResult.winners }} 张 → winners/</p>
      <p>淘汰: {{ exportResult.losers }} 张 → losers/</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const photos = ref([])
const mode = ref('copy')
const exporting = ref(false)
const exportResult = ref(null)

const winners = computed(() => photos.value.filter(p => !p.is_rejected))
const losersCount = computed(() => photos.value.filter(p => p.is_rejected).length)

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

async function doExport() {
  exporting.value = true
  try {
    const res = await axios.post('/api/export/final', null, {
      params: { mode: mode.value }
    })
    exportResult.value = res.data
  } catch (e) {
    alert('导出失败: ' + e.message)
  } finally {
    exporting.value = false
  }
}

onMounted(loadPhotos)
</script>

<style scoped>
.confirm-view { padding: 1.5rem 2rem; }
.confirm-view h2 { margin-bottom: 0.5rem; }
.confirm-view p { color: #aaa; margin-bottom: 1rem; }
.confirm-stats { display: flex; gap: 2rem; margin-bottom: 1rem; }
.confirm-stats strong { color: #4caf50; }
.confirm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.8rem; max-height: 50vh; overflow-y: auto; margin-bottom: 1.5rem; }
.confirm-card { position: relative; border-radius: 8px; overflow: hidden; border: 2px solid #4caf50; }
.confirm-card img { width: 100%; height: 100px; object-fit: cover; }
.card-score { position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.7); color: #4caf50; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }
.confirm-actions { text-align: center; }
.mode-select { display: flex; gap: 1rem; align-items: center; justify-content: center; margin-bottom: 1rem; }
.mode-select label { color: #aaa; cursor: pointer; }
.export-btn { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.export-btn:disabled { opacity: 0.5; }
.export-result { text-align: center; margin-top: 1.5rem; background: #16213e; padding: 1.5rem; border-radius: 12px; }
</style>
