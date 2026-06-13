<template>
  <div class="confirm-view">
    <h2>最终确认</h2>

    <!-- PK not complete -->
    <div v-if="!pkComplete" class="not-ready">
      <p class="not-ready-msg">请先完成所有选片</p>
      <p class="not-ready-info">
        已完成 {{ pkStatus.finished_groups }} / {{ pkStatus.total_groups }} 组
      </p>
      <p class="not-ready-info">
        已选中 {{ pkStatus.selected_count }} 张照片
      </p>
      <button class="go-pick-btn" @click="$router.push('/pick')">去选片 →</button>
    </div>

    <!-- PK complete -->
    <div v-else>
      <div class="confirm-stats">
        <span>入选: <strong>{{ selectedPhotos.length }}</strong> 张</span>
        <span>未入选: <strong>{{ rejectedCount }}</strong> 张</span>
      </div>

      <div class="confirm-grid">
        <div v-for="photo in selectedPhotos" :key="photo.id" class="confirm-card">
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
        <p>入选: {{ exportResult['入选'] }} 张</p>
        <p>未入选: {{ exportResult['未入选'] }} 张</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const allPhotos = ref([])
const pkStatus = ref({ complete: false, total_groups: 0, finished_groups: 0, selected_count: 0 })
const mode = ref('copy')
const exporting = ref(false)
const exportResult = ref(null)

const pkComplete = computed(() => pkStatus.value.complete)
const selectedPhotos = computed(() => allPhotos.value.filter(p => p.is_selected))
const rejectedCount = computed(() => allPhotos.value.filter(p => p.is_rejected).length)

async function loadStatus() {
  try {
    const res = await axios.get('/api/pk/status')
    pkStatus.value = res.data
  } catch {}
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  allPhotos.value = res.data
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

onMounted(() => {
  loadStatus()
  loadPhotos()
})
</script>

<style scoped>
.confirm-view { padding: 1.5rem 2rem; }
.confirm-view h2 { margin-bottom: 0.5rem; text-align: center; }
.not-ready { text-align: center; padding: 4rem 0; }
.not-ready-msg { font-size: 1.3rem; color: #ff9800; margin-bottom: 1rem; }
.not-ready-info { color: #888; margin-bottom: 0.5rem; }
.go-pick-btn { margin-top: 1.5rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.confirm-stats { display: flex; gap: 2rem; justify-content: center; margin-bottom: 1rem; }
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
