<template>
  <div class="pick-view">
    <div v-if="currentGroup" class="pick-area">
      <div class="pick-header">
        <h3>场景 {{ groupIndex + 1 }}/{{ groups.length }} — {{ currentGroup.id }} ({{ pkIndex + 1 }}/{{ pkPairs.length }})</h3>
        <div class="pick-actions">
          <button class="action-btn" @click="skipGroup">跳过本组 (S)</button>
          <button class="action-btn" @click="undoPk">撤销 (Shift+Z)</button>
          <button class="action-btn" @click="cycleZoom">缩放 {{ zoomLevel }}x (Z)</button>
        </div>
      </div>
      <PKBattle
        v-if="pkPairs.length > 0"
        :left="pkPairs[pkIndex][0]"
        :right="pkPairs[pkIndex][1]"
        @choose="onChoose"
        @zoom="openZoom"
      />
    </div>

    <div v-else class="pick-done">
      <h3>✅ 所有场景PK完成</h3>
      <p>已选 {{ selectedCount }} 张照片</p>
      <button @click="$router.push('/confirm')">去导出 →</button>
    </div>

    <RejectedPool :photos="rejectedPhotos" @rescue="rescuePhoto" />
    <ZoomViewer :visible="zoomVisible" :left-src="zoomLeftSrc" :right-src="zoomRightSrc" @close="zoomVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import PKBattle from '../components/PKBattle.vue'
import RejectedPool from '../components/RejectedPool.vue'
import ZoomViewer from '../components/ZoomViewer.vue'

const photos = ref([])
const groups = ref([])
const groupIndex = ref(0)
const pkIndex = ref(0)
const zoomVisible = ref(false)
const zoomLeftSrc = ref('')
const zoomRightSrc = ref('')
const zoomLevel = ref(1)
const zoomLevels = [1, 2, 4]

const currentGroup = computed(() => groups.value[groupIndex.value] || null)

const pkPairs = computed(() => {
  if (!currentGroup.value) return []
  const pids = currentGroup.value.photos
  const pairs = []
  for (let i = 0; i < pids.length - 1; i += 2) {
    const left = photos.value.find(p => p.id === pids[i])
    const right = photos.value.find(p => p.id === pids[i + 1])
    if (left && right) pairs.push([left, right])
  }
  return pairs
})

const selectedCount = computed(() => photos.value.filter(p => p.is_selected).length)
const rejectedPhotos = computed(() => photos.value.filter(p => p.is_rejected))

function getPhoto(id) {
  return photos.value.find(p => p.id === id)
}

async function onChoose(side) {
  if (!pkPairs.value[pkIndex.value]) return
  const [left, right] = pkPairs.value[pkIndex.value]

  if (side === 'left') {
    await axios.post('/api/pk/submit', { winner_id: left.id, loser_id: right.id })
  } else if (side === 'right') {
    await axios.post('/api/pk/submit', { winner_id: right.id, loser_id: left.id })
  } else if (side === 'both') {
    await axios.post(`/api/photos/${left.id}/select`)
    await axios.post(`/api/photos/${right.id}/select`)
  }

  if (pkIndex.value < pkPairs.value.length - 1) {
    pkIndex.value++
  } else {
    groupIndex.value++
    pkIndex.value = 0
  }

  await loadPhotos()
}

function cycleZoom() {
  const idx = zoomLevels.indexOf(zoomLevel.value)
  zoomLevel.value = zoomLevels[(idx + 1) % zoomLevels.length]
}

async function skipGroup() {
  try {
    await axios.post('/api/pk/skip')
    groupIndex.value++
    pkIndex.value = 0
    await loadPhotos()
  } catch (e) {
    alert('跳过失败: ' + e.message)
  }
}

async function undoPk() {
  try {
    await axios.post('/api/pk/undo')
    await loadPhotos()
    await loadGroups()
    if (pkIndex.value > 0) {
      pkIndex.value--
    } else if (groupIndex.value > 0) {
      groupIndex.value--
      pkIndex.value = 0
    }
  } catch (e) {
    alert('撤销失败: ' + e.message)
  }
}

function openZoom(leftId, rightId) {
  zoomLeftSrc.value = '/api/preview/' + leftId
  zoomRightSrc.value = '/api/preview/' + rightId
  zoomVisible.value = true
}

function handleKeydown(e) {
  if (e.key === 's' || e.key === 'S') {
    e.preventDefault()
    skipGroup()
  } else if (e.key === 'Z' && e.shiftKey) {
    e.preventDefault()
    undoPk()
  } else if (e.key === 'z' && !e.shiftKey) {
    e.preventDefault()
    cycleZoom()
  }
}

async function rescuePhoto(id) {
  await axios.post(`/api/photos/${id}/rescue`)
  await loadPhotos()
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

async function loadGroups() {
  const res = await axios.get('/api/groups')
  groups.value = res.data
}

onMounted(() => {
  loadPhotos()
  loadGroups()
  window.addEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.pick-view { padding: 1.5rem 2rem; }
.pick-area h3 { margin-bottom: 1rem; color: #aaa; }
.pick-done { text-align: center; padding: 4rem 0; }
.pick-done button { margin-top: 1.5rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.pick-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.pick-header h3 { color: #aaa; margin: 0; }
.pick-actions { display: flex; gap: 0.5rem; }
.action-btn { padding: 0.4rem 0.8rem; background: #16213e; color: #aaa; border: 1px solid #333; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.action-btn:hover { background: #1a5276; color: #fff; }
</style>
