<template>
  <div class="pick-view">
    <!-- Arena mode: processing groups -->
    <div v-if="!allDone" class="pick-area">
      <div class="pick-header">
        <h3>
          <template v-if="isSingle">
            独立照片审核（剩余 {{ singleRemaining }} 张）
          </template>
          <template v-else>
            场景 {{ finishedGroups + 1 }} / {{ totalGroups }}
            · 已选 {{ winnersCount }} · 已淘汰 {{ losersCount }} · 待比较 {{ pendingCount + 2 }}
          </template>
        </h3>
        <div class="pick-actions">
          <button class="action-btn" @click="undoPk">撤销 (Shift+Z)</button>
        </div>
      </div>

      <PKBattle
        :left="leftPhoto"
        :right="rightPhoto"
        :is-single="isSingle"
        @choose="onChoose"
        @zoom="openZoom"
      />

      <div class="zoom-guide">
        <template v-if="isSingle">
          快捷键: ← 入选 | → 不要
        </template>
        <template v-else>
          点击查看高清 · ← 保留左 → 保留右 · ↑ 全部保留 · ↓ 暂缓
        </template>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
        <span class="progress-text">{{ finishedGroups }} / {{ totalGroups }} 场景完成</span>
      </div>
    </div>

    <!-- All done -->
    <div v-else class="pick-done">
      <h3>甄选完成</h3>
      <p>已保留 {{ selectedCount }} 张 · 已淘汰 {{ rejectedCount }} 张</p>
      <button @click="$router.push('/confirm')">审阅待定照片 →</button>
    </div>

    <ZoomViewer :visible="zoomVisible" :left-src="zoomLeftSrc" :right-src="zoomRightSrc" @close="zoomVisible = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import PKBattle from '../components/PKBattle.vue'
import ZoomViewer from '../components/ZoomViewer.vue'

const router = useRouter()

// PK state from backend
const pkState = ref(null)
const photos = ref([])
const zoomVisible = ref(false)
const zoomLeftSrc = ref('')
const zoomRightSrc = ref('')
const loading = ref(false)

// Computed from pkState
const allDone = computed(() => pkState.value?.done === true)
const isSingle = computed(() => pkState.value?.is_single || false)
const groupSize = computed(() => pkState.value?.group_size || 0)
const decidedCount = computed(() => pkState.value?.decided_count || 0)
const winnersCount = computed(() => pkState.value?.winners_count || 0)
const losersCount = computed(() => pkState.value?.losers_count || 0)
const pendingCount = computed(() => pkState.value?.pending_count || 0)
const totalGroups = computed(() => pkState.value?.total_groups || 0)
const finishedGroups = computed(() => pkState.value?.finished_groups || 0)
const singleRemaining = computed(() => pkState.value?.single_remaining || 0)
const selectedCount = computed(() => pkState.value?.selected_count || 0)
const rejectedCount = computed(() => pkState.value?.rejected_count || 0)
const progressPct = computed(() => {
  if (!totalGroups.value) return 0
  return Math.round((finishedGroups.value / totalGroups.value) * 100)
})

const leftPhoto = computed(() => {
  if (!pkState.value?.left) return null
  return photos.value.find(p => p.id === pkState.value.left) || null
})
const rightPhoto = computed(() => {
  if (!pkState.value?.right) return null
  return photos.value.find(p => p.id === pkState.value.right) || null
})

async function loadPkState() {
  try {
    const res = await axios.get('/api/pk/current')
    pkState.value = res.data
  } catch (e) {
    console.error('Failed to load PK state:', e)
  }
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

async function onChoose(action) {
  if (loading.value || !pkState.value || pkState.value.done) return
  loading.value = true
  try {
    const groupId = pkState.value.group_id
    await axios.post(`/api/pk/advance?group_id=${groupId}&action=${action}`)
    await loadPhotos()
    await loadPkState()
  } catch (e) {
    alert('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function undoPk() {
  try {
    const groupId = pkState.value?.group_id
    const params = groupId ? `?group_id=${groupId}` : ''
    await axios.post('/api/pk/undo' + params)
    await loadPhotos()
    await loadPkState()
  } catch (e) {
    alert('撤销失败: ' + (e.response?.data?.detail || e.message))
  }
}

function openZoom(leftId, rightId) {
  zoomLeftSrc.value = '/api/preview/' + leftId
  zoomRightSrc.value = rightId ? '/api/preview/' + rightId : ''
  zoomVisible.value = true
}

function handleKeydown(e) {
  if (zoomVisible.value || allDone.value) return

  if (isSingle.value) {
    // Single mode: ← keep, → reject
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      onChoose('keep')
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      onChoose('reject')
    }
  } else {
    // Multi mode: arena
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      onChoose('left')
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      onChoose('right')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      onChoose('both')
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      onChoose('none')
    }
  }

  if (e.key === 'Z' && e.shiftKey) {
    e.preventDefault()
    undoPk()
  }
}

onMounted(async () => {
  await loadPhotos()
  await loadPkState()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.pick-view { padding: 1.5rem 2rem; }
.pick-area h3 { margin-bottom: 1rem; color: #aaa; }
.pick-done { text-align: center; padding: 4rem 0; }
.pick-done h3 { font-size: 1.5rem; margin-bottom: 1rem; }
.pick-done p { color: #888; margin-bottom: 1.5rem; }
.pick-done button { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.pick-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.pick-header h3 { color: #aaa; margin: 0; font-size: 0.95rem; }
.pick-actions { display: flex; gap: 0.5rem; }
.action-btn { padding: 0.4rem 0.8rem; background: #16213e; color: #aaa; border: 1px solid #333; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.action-btn:hover { background: #1a5276; color: #fff; }
.zoom-guide { text-align: center; color: #666; font-size: 0.8rem; margin-top: 0.5rem; padding: 0.5rem; background: #111; border-radius: 6px; }
.progress-bar { position: relative; height: 24px; background: #1a1a2e; border-radius: 12px; margin-top: 1rem; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #0f3460, #4caf50); border-radius: 12px; transition: width 0.3s ease; }
.progress-text { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; color: #ccc; }
</style>
