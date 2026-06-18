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
            · 已选 {{ winnersCount }} · 已淘汰 {{ losersCount }} · 暂存 {{ heldCount }}
          </template>
        </h3>
        <div class="pick-actions">
          <button class="action-btn" @click="undoPk">撤销 (Shift+Z)</button>
          <button class="action-btn" @click="showPersonOverview = !showPersonOverview">人物统计 (Space)</button>
        </div>
      </div>

      <PKBattle
        :left="leftPhoto"
        :right="rightPhoto"
        :is-single="isSingle"
        @choose="onChoose"
        @zoom="openZoom"
      />

      <div class="pick-controls">
        <template v-if="isSingle">
          <button class="control-btn keep" @click="onChoose('keep')">← 入选</button>
          <button class="control-btn hold" @click="onChoose('hold')">暂存</button>
          <button class="control-btn reject" @click="onChoose('reject')">不要 →</button>
        </template>
        <template v-else>
          <button class="control-btn keep" @click="onChoose('left')">← 选左</button>
          <button class="control-btn keep" @click="onChoose('both')">↑ 两张都要</button>
          <button class="control-btn hold" @click="onChoose('hold')">暂存</button>
          <button class="control-btn reject" @click="onChoose('none')">↓ 两张都不要</button>
          <button class="control-btn keep" @click="onChoose('right')">选右 →</button>
        </template>
      </div>

      <div class="zoom-guide">
        <template v-if="isSingle">
          快捷键: ← 入选 | → 不要
        </template>
        <template v-else>
          快捷键: ← 选左 | → 选右 | ↑ 两张都要 | ↓ 两张都不要 | Space 人物统计
        </template>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
        <span class="progress-text">{{ finishedGroups }} / {{ totalGroups }} 场景完成</span>
      </div>

      <!-- Person overview overlay -->
      <div v-if="showPersonOverview" class="person-overlay" @click="showPersonOverview = false">
        <div class="person-stats" @click.stop>
          <h4>人物统计</h4>
          <div v-if="personStats.length === 0" class="no-persons">
            未检测到人物
          </div>
          <div v-for="person in personStats" :key="person.id" class="person-row">
            <div class="person-thumbs">
              <img v-for="(photoId, idx) in person.sample_photos.slice(0, 2)" :key="idx"
                   :src="'/api/thumbnail/' + photoId" class="person-thumb" />
            </div>
            <span class="person-name">{{ person.name }}</span>
            <span class="person-count">{{ person.count }} 张</span>
          </div>
          <p class="overlay-hint">点击任意处关闭</p>
        </div>
      </div>
    </div>

    <!-- All done -->
    <div v-else class="pick-done">
      <h3>PK 完成</h3>
      <p>已选 {{ selectedCount }} 张 · 已淘汰 {{ rejectedCount }} 张 · 暂存 {{ heldCount }} 张</p>
      <button @click="$router.push('/confirm')">确认导出 →</button>
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
const showPersonOverview = ref(false)

// Computed from pkState
const allDone = computed(() => pkState.value?.done === true)
const isSingle = computed(() => pkState.value?.is_single || false)
const groupSize = computed(() => pkState.value?.group_size || 0)
const decidedCount = computed(() => pkState.value?.decided_count || 0)
const winnersCount = computed(() => pkState.value?.winners_count || 0)
const losersCount = computed(() => pkState.value?.losers_count || 0)
const heldCount = computed(() => pkState.value?.held_count || 0)
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

const personStats = ref([])

async function loadPersonStats() {
  try {
    const res = await axios.get('/api/persons')
    personStats.value = res.data
  } catch {}
}

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

  // Space for person overview
  if (e.key === ' ' && !e.repeat) {
    e.preventDefault()
    showPersonOverview.value = !showPersonOverview.value
    return
  }

  if (showPersonOverview.value) return

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
  await loadPersonStats()
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
.pick-controls { display: flex; justify-content: center; gap: 1rem; margin-top: 1rem; }
.control-btn { padding: 0.6rem 1.2rem; border: none; border-radius: 8px; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; }
.control-btn.keep { background: #1a5276; color: #fff; }
.control-btn.keep:hover { background: #2980b9; }
.control-btn.hold { background: #7d6608; color: #fff; }
.control-btn.hold:hover { background: #9a7d0a; }
.control-btn.reject { background: #922b21; color: #fff; }
.control-btn.reject:hover { background: #c0392b; }
.zoom-guide { text-align: center; color: #666; font-size: 0.8rem; margin-top: 0.5rem; padding: 0.5rem; background: #111; border-radius: 6px; }
.progress-bar { position: relative; height: 24px; background: #1a1a2e; border-radius: 12px; margin-top: 1rem; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #0f3460, #4caf50); border-radius: 12px; transition: width 0.3s ease; }
.progress-text { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; color: #ccc; }

/* Person overview overlay */
.person-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.person-stats { background: #16213e; border-radius: 12px; padding: 1.5rem; min-width: 300px; max-width: 400px; }
.person-stats h4 { margin-bottom: 1rem; color: #4cc9f0; }
.no-persons { color: #888; text-align: center; padding: 1rem; }
.person-row { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.8rem; padding: 0.5rem; background: #1a1a2e; border-radius: 8px; }
.person-thumbs { display: flex; gap: 4px; }
.person-thumb { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; border: 2px solid #4cc9f0; }
.person-name { flex: 1; color: #aaa; font-size: 0.9rem; }
.person-count { color: #888; font-size: 0.8rem; }
.overlay-hint { text-align: center; color: #666; font-size: 0.75rem; margin-top: 1rem; }
</style>
