<template>
  <div class="filter-view">
    <GradeSelector :selected="gradeLevel" @change="changeGrade" />

    <div class="filter-stats">
      <span class="stat green">🟢 {{ gradeCounts.green }}</span>
      <span class="stat yellow">🟡 {{ gradeCounts.yellow }}</span>
      <span class="stat red">🔴 {{ gradeCounts.red }}</span>
      <button class="detect-btn" @click="runDetection" :disabled="detecting">
        {{ detecting ? '检测中...' : '开始检测' }}
      </button>
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
          </div>
        </div>
      </div>
    </div>

    <RejectedPool :photos="rejectedPhotos" @rescue="rescuePhoto" />

    <div class="next-step">
      <button @click="$router.push('/pick')">进入PK选片 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import GradeSelector from '../components/GradeSelector.vue'
import RejectedPool from '../components/RejectedPool.vue'

const photos = ref([])
const groups = ref([])
const gradeLevel = ref(60)
const detecting = ref(false)

const gradeCounts = computed(() => {
  const counts = { green: 0, yellow: 0, red: 0 }
  photos.value.forEach(p => counts[p.grade]++)
  return counts
})

const rejectedPhotos = computed(() => photos.value.filter(p => p.is_rejected))

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

async function runDetection() {
  detecting.value = true
  await axios.post('/api/detect')
  await loadPhotos()
  detecting.value = false
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

onMounted(() => {
  loadPhotos()
  loadGroups()
})
</script>

<style scoped>
.filter-view { padding: 1.5rem 2rem; }
.filter-stats { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; }
.stat { font-size: 1.1rem; padding: 0.3rem 0.8rem; border-radius: 6px; }
.detect-btn { padding: 0.5rem 1.5rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; cursor: pointer; margin-left: auto; }
.detect-btn:disabled { opacity: 0.5; }
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
</style>
