<template>
  <div class="filter-view">
    <GradeSelector :selected="gradeLevel" @change="changeGrade" />

    <div class="threshold-bar">
      <label>质量阈值: {{ threshold.toFixed(2) }}</label>
      <input type="range" v-model.number="threshold" min="0.5" max="0.95" step="0.05" @change="onThresholdChange" />
    </div>

    <div class="filter-stats">
      <span class="stat green">🟢 {{ gradeCounts.green }}</span>
      <span class="stat yellow">🟡 {{ gradeCounts.yellow }}</span>
      <span class="stat red">🔴 {{ gradeCounts.red }}</span>
      <span class="runtime-info">设备: {{ runtimeDevice }} ({{ runtimeDevice === 'cpu' ? 'CPU' : 'GPU' }})</span>
      <button class="runtime-toggle" @click="cycleRuntime">
        {{ runtimePreference === 'auto' ? '自动' : runtimePreference === 'gpu' ? 'GPU' : 'CPU' }}
      </button>
      <button class="detect-btn" @click="runDetection" :disabled="detecting">
        {{ detecting ? '检测中...' : '开始检测' }}
      </button>
      <button class="detect-btn" @click="runGrouping" :disabled="grouping" style="background: #1a5276;">
        {{ grouping ? '分组中...' : '开始分组' }}
      </button>
    </div>

    <div v-if="progress.status !== 'idle' && progress.status !== 'done'" class="progress-bar-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <span class="progress-label">{{ progress.label }} {{ progress.done }}/{{ progress.total }}</span>
      <span v-if="etaText" class="progress-eta">预计剩余: {{ etaText }}</span>
    </div>

    <div class="group-list">
      <div v-for="group in groups" :key="group.id" class="group-card">
        <h4>{{ group.id }} ({{ group.photos.length }}张)</h4>
        <div class="group-thumbs">
          <div
            v-for="pid in group.photos"
            :key="pid"
            class="thumb"
            :class="{ selected: getPhoto(pid)?.is_selected, rejected: getPhoto(pid)?.is_rejected }"
          >
            <img :src="'/api/thumbnail/' + pid" loading="lazy" />
            <span class="thumb-score">{{ getPhoto(pid)?.score }}</span>
            <div v-if="getPhoto(pid)?.rejection_reasons?.length" class="thumb-reasons">
              <span v-for="r in getPhoto(pid).rejection_reasons" :key="r" class="reason-badge">{{ r }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <RejectedPool :photos="rejectedPhotos" @rescue="rescuePhoto" />

    <div class="next-step">
      <p v-if="groups.length === 0" style="color: #ff9800; margin-bottom: 0.5rem;">请先点击"开始分组"再进入PK</p>
      <button @click="$router.push('/pick')">进入PK选片 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import GradeSelector from '../components/GradeSelector.vue'
import RejectedPool from '../components/RejectedPool.vue'

const photos = ref([])
const groups = ref([])
const gradeLevel = ref(60)
const detecting = ref(false)
const grouping = ref(false)
const threshold = ref(0.75)
const runtimeDevice = ref('cpu')
const runtimePreference = ref('auto')
const progress = ref({ status: 'idle', done: 0, total: 0, label: '' })
let progressTimer = null
let progressStartTime = 0

const gradeCounts = computed(() => {
  const counts = { green: 0, yellow: 0, red: 0 }
  photos.value.forEach(p => counts[p.grade]++)
  return counts
})

const rejectedPhotos = computed(() => photos.value.filter(p => p.is_rejected))

const progressPercent = computed(() => {
  if (progress.value.total === 0) return 0
  return Math.round((progress.value.done / progress.value.total) * 100)
})

const etaText = computed(() => {
  if (progress.value.done === 0 || progress.value.total === 0) return ''
  const elapsed = (Date.now() - progressStartTime) / 1000
  const perItem = elapsed / progress.value.done
  const remaining = perItem * (progress.value.total - progress.value.done)
  if (remaining < 60) return `${Math.round(remaining)}秒`
  return `${Math.round(remaining / 60)}分钟`
})

function getPhoto(id) {
  return photos.value.find(p => p.id === id)
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

async function loadGroups() {
  const res = await axios.get('/api/groups')
  groups.value = res.data
}

function startProgressPolling() {
  progressStartTime = Date.now()
  progressTimer = setInterval(async () => {
    try {
      const res = await axios.get('/api/progress')
      progress.value = res.data
      if (res.data.status === 'done') {
        stopProgressPolling()
      }
    } catch (e) {
      // ignore polling errors
    }
  }, 500)
}

function stopProgressPolling() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

async function runDetection() {
  detecting.value = true
  startProgressPolling()
  await axios.post('/api/detect')
  stopProgressPolling()
  progress.value = { status: 'idle', done: 0, total: 0, label: '' }
  await loadPhotos()
  detecting.value = false
}

async function runGrouping() {
  grouping.value = true
  startProgressPolling()
  try {
    const res = await axios.post('/api/group')
    stopProgressPolling()
    progress.value = { status: 'idle', done: 0, total: 0, label: '' }
    await loadGroups()
    await loadPhotos()
    const method = res.data.method === 'clip' ? 'CLIP语义分组' : 'pHash感知哈希'
    alert(`分组完成！共 ${res.data.groups} 个场景（使用 ${method}）`)
  } catch (e) {
    stopProgressPolling()
    progress.value = { status: 'idle', done: 0, total: 0, label: '' }
    alert('分组失败: ' + e.message)
  } finally {
    grouping.value = false
  }
}

async function changeGrade(level) {
  gradeLevel.value = level
  await axios.post('/api/filter/grade', null, { params: { level } })
  await loadPhotos()
}

async function rescuePhoto(id) {
  await axios.post(`/api/photos/${id}/rescue`)
  await loadPhotos()
}

async function onThresholdChange() {
  await axios.post('/api/groups/threshold', null, { params: { threshold: threshold.value } })
  await loadGroups()
  await loadPhotos()
}

async function loadRuntime() {
  const res = await axios.get('/api/runtime')
  runtimeDevice.value = res.data.device
  runtimePreference.value = res.data.preference
}

async function cycleRuntime() {
  const order = ['auto', 'gpu', 'cpu']
  const next = order[(order.indexOf(runtimePreference.value) + 1) % order.length]
  const res = await axios.post('/api/runtime', null, { params: { preference: next } })
  runtimePreference.value = res.data.preference
  runtimeDevice.value = res.data.device
}

onMounted(() => {
  loadPhotos()
  loadGroups()
  loadRuntime()
})

onUnmounted(() => {
  stopProgressPolling()
})
</script>

<style scoped>
.filter-view { padding: 1.5rem 2rem; }
.filter-stats { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; }
.stat { font-size: 1.1rem; padding: 0.3rem 0.8rem; border-radius: 6px; }
.detect-btn { padding: 0.5rem 1.5rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; cursor: pointer; margin-left: auto; }
.detect-btn:disabled { opacity: 0.5; }
.runtime-info { font-size: 0.9rem; color: #aaa; padding: 0.3rem 0.6rem; background: #16213e; border-radius: 6px; }
.runtime-toggle { padding: 0.4rem 0.8rem; background: #2c3e50; color: #fff; border: 1px solid #444; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.runtime-toggle:hover { background: #34495e; }
.progress-bar-container { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; padding: 0.8rem 1rem; background: #16213e; border-radius: 8px; }
.progress-bar { flex: 1; height: 8px; background: #333; border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: #4caf50; border-radius: 4px; transition: width 0.3s; }
.progress-label { color: #eee; font-size: 0.9rem; white-space: nowrap; }
.progress-eta { color: #aaa; font-size: 0.85rem; white-space: nowrap; }
.group-list { display: flex; flex-direction: column; gap: 1rem; max-height: 50vh; overflow-y: auto; }
.group-card { background: #16213e; border-radius: 8px; padding: 1rem; }
.group-card h4 { margin-bottom: 0.5rem; color: #aaa; }
.group-thumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.thumb { position: relative; width: 120px; height: 80px; border-radius: 6px; overflow: hidden; border: 2px solid transparent; }
.thumb.selected { border-color: #4caf50; }
.thumb.rejected { border-color: #f44336; opacity: 0.5; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.thumb-score { position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.7); color: #fff; font-size: 0.7rem; padding: 1px 4px; border-radius: 3px; }
.next-step { margin-top: 2rem; text-align: center; }
.next-step button { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.next-step button:hover { background: #1a5276; }
.threshold-bar { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; color: #aaa; }
.threshold-bar input[type=range] { flex: 1; max-width: 300px; }
.thumb-reasons { position: absolute; bottom: 2px; left: 2px; right: 2px; display: flex; gap: 2px; flex-wrap: wrap; }
.reason-badge { background: rgba(244,67,54,0.85); color: #fff; font-size: 0.55rem; padding: 1px 3px; border-radius: 2px; }
</style>
