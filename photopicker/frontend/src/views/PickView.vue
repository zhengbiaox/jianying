<template>
  <div class="pick-view">
    <div v-if="currentGroup" class="pick-area">
      <h3>{{ currentGroup.id }} ({{ pkIndex + 1 }}/{{ pkPairs.length }})</h3>
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
      <button @click="$router.push('/export')">去导出 →</button>
    </div>

    <RejectedPool :photos="rejectedPhotos" @rescue="rescuePhoto" />
    <ZoomViewer :src="zoomSrc" :visible="zoomVisible" @close="zoomVisible = false" />
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
const zoomSrc = ref('')

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

async function openZoom(id) {
  const photo = getPhoto(id)
  if (photo) {
    zoomSrc.value = '/api/thumbnail/' + id
    zoomVisible.value = true
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
})
</script>

<style scoped>
.pick-view { padding: 1.5rem 2rem; }
.pick-area h3 { margin-bottom: 1rem; color: #aaa; }
.pick-done { text-align: center; padding: 4rem 0; }
.pick-done button { margin-top: 1.5rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
</style>
