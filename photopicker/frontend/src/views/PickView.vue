<template>
  <div class="pick-view">
    <div v-if="currentGroup" class="pick-area">
      <a-space style="margin-bottom: 1rem;">
        <a-tag color="blue">场景 {{ groupIndex + 1 }} / {{ groups.length }}</a-tag>
        <a-tag>第 {{ pkIndex + 1 }} / {{ pkPairs.length }} 对</a-tag>
        <a-button type="text" size="small" @click="skipGroup">跳过此场景 (S)</a-button>
        <a-button type="text" size="small" @click="undoPk">撤销 (Shift+Z)</a-button>
      </a-space>
      
      <PKBattle
        v-if="pkPairs.length > 0"
        :left="pkPairs[pkIndex][0]"
        :right="pkPairs[pkIndex][1]"
        @choose="onChoose"
        @zoom="openZoom"
      />
      
      <a-alert type="info" style="margin-top: 0.5rem;">
        点击查看高清 · ← 保留左 → 保留右 · ↑ 全部保留 · ↓ 暂缓
      </a-alert>
    </div>
    
    <a-result v-else status="success" title="甄选完成" :subtitle="`已保留 ${selectedCount} 张`">
      <template #extra>
        <a-button type="primary" @click="$router.push('/pending')">审阅待定照片 →</a-button>
      </template>
    </a-result>
    
    <a-divider />
    <RejectedPool :photos="rejectedPhotos" @rescue="rescuePhoto" />
    <ZoomViewer :visible="zoomVisible" :left-src="zoomLeftSrc" :right-src="zoomRightSrc" @close="zoomVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

const currentGroup = computed(() => groups.value[groupIndex.value] || null)

const pkPairs = computed(() => {
  if (!currentGroup.value) return []
  const pids = currentGroup.value.photos
  const availablePids = pids.filter(pid => {
    const photo = photos.value.find(p => p.id === pid)
    return photo && !photo.is_rejected && !photo.is_pending
  })
  const pairs = []
  for (let i = 0; i < availablePids.length - 1; i += 2) {
    const left = photos.value.find(p => p.id === availablePids[i])
    const right = photos.value.find(p => p.id === availablePids[i + 1])
    if (left && right) pairs.push([left, right])
  }
  return pairs
})

const selectedCount = computed(() => photos.value.filter(p => p.is_selected).length)
const rejectedPhotos = computed(() => photos.value.filter(p => p.is_rejected))

function getPhoto(id) { return photos.value.find(p => p.id === id) }

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
  } else if (side === 'none') {
    await axios.post('/api/pk/skip_pair', [left.id, right.id])
  }
  if (pkIndex.value < pkPairs.value.length - 1) {
    pkIndex.value++
  } else {
    groupIndex.value++
    pkIndex.value = 0
  }
  await loadPhotos()
}

async function skipGroup() {
  try {
    await axios.post('/api/pk/skip')
    groupIndex.value++
    pkIndex.value = 0
    await loadPhotos()
  } catch {}
}

async function undoPk() {
  try {
    await axios.post('/api/pk/undo')
    await loadPhotos()
    await loadGroups()
    if (pkIndex.value > 0) pkIndex.value--
    else if (groupIndex.value > 0) { groupIndex.value--; pkIndex.value = 0 }
  } catch {}
}

function openZoom(leftId, rightId) {
  zoomLeftSrc.value = '/api/preview/' + leftId
  zoomRightSrc.value = '/api/preview/' + rightId
  zoomVisible.value = true
}

function handleKeydown(e) {
  if (zoomVisible.value) return
  if (e.key === 'ArrowLeft') { e.preventDefault(); onChoose('left') }
  else if (e.key === 'ArrowRight') { e.preventDefault(); onChoose('right') }
  else if (e.key === 'ArrowUp') { e.preventDefault(); onChoose('both') }
  else if (e.key === 'ArrowDown') { e.preventDefault(); onChoose('none') }
  else if (e.key === 's' || e.key === 'S') { e.preventDefault(); skipGroup() }
  else if (e.key === 'Z' && e.shiftKey) { e.preventDefault(); undoPk() }
}

async function rescuePhoto(id) { await axios.post(`/api/photos/${id}/rescue`); await loadPhotos() }
async function loadPhotos() { photos.value = (await axios.get('/api/photos')).data }
async function loadGroups() { groups.value = (await axios.get('/api/groups')).data }

onMounted(() => { loadPhotos(); loadGroups(); window.addEventListener('keydown', handleKeydown) })
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.pick-view { padding: 1.5rem 2rem; }
</style>
