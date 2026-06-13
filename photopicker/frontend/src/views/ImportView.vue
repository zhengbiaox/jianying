<template>
  <div class="import-view">
    <!-- Phase 1: Directory selection -->
    <div v-if="phase === 'select'">
      <h2>PhotoPicker</h2>
      <div class="browser">
        <div class="browser-path">
          <span class="path-label">当前路径:</span>
          <span class="path-text">{{ currentPath }}</span>
          <button class="up-btn" @click="goUp" :disabled="!parentPath">↑ 上级</button>
          <button class="native-btn" @click="nativePick">浏览</button>
        </div>
        <div class="dir-list">
          <div v-for="dir in dirs" :key="dir.path" class="dir-item" @click="navigate(dir.path)">
            📁 {{ dir.name }}
          </div>
          <div v-if="dirs.length === 0" class="empty">此目录下没有子文件夹</div>
        </div>
        <div class="folder-preview" v-if="preview">
          <p>        已识别 <strong>{{ preview.count }}</strong> 张照片，共 <strong>{{ preview.size_mb }} MB</strong></p>
        </div>
      </div>
      <div class="options">
        <div class="option-group">
          <label>处理引擎:</label>
          <div class="radio-group">
            <label><input type="radio" v-model="runtime" value="auto" /> 自动检测</label>
            <label><input type="radio" v-model="runtime" value="cpu" /> CPU</label>
            <label><input type="radio" v-model="runtime" value="gpu" /> GPU</label>
          </div>
        </div>
        <div class="option-group">
          <label>甄选策略:</label>
          <div class="radio-group">
            <label><input type="radio" v-model="filterLevel" value="80" /> 🟢 精选 · 严格</label>
            <label><input type="radio" v-model="filterLevel" value="60" /> 🟡 均衡 · 推荐</label>
            <label><input type="radio" v-model="filterLevel" value="40" /> 🔴 宽泛 · 保守</label>
          </div>
        </div>
      </div>
      <button class="start-btn" @click="startProcess" :disabled="!currentPath">
        开始分析
      </button>
      <div class="reset-section">
        <button class="reset-btn" @click="doReset">重新开始</button>
        <p class="reset-hint">清除所有缓存与进度</p>
      </div>
    </div>

    <!-- Phase 2: Processing with photo wall -->
    <div v-if="phase === 'processing'" class="processing">
      <div class="progress-header">
        <h3>正在逐帧分析...</h3>
        <button class="stop-btn" @click="stopProcess">停止</button>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
      </div>
      <div class="progress-info">
        <span>{{ processStatus.done }} / {{ processStatus.total }}</span>
        <span>建议淘汰: {{ processStatus.rejected_count }} 张</span>
        <span v-if="eta">预计剩余: {{ eta }}</span>
      </div>
      <div class="photo-wall">
        <div v-for="ev in recentEvents" :key="ev.id"
             class="wall-cell" :class="{ rejected: ev.rejected, ok: !ev.rejected }">
          <img :src="'/api/thumbnail/' + ev.id" loading="lazy" />
          <div class="wall-overlay">
            <span class="wall-score">{{ ev.score }}</span>
            <span v-if="ev.rejected" class="wall-reason">{{ ev.reasons[0] || '建议淘汰' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase 3: Done -->
    <div v-if="phase === 'done'" class="done">
      <h3>✅ 分析完成</h3>
      <div class="done-stats">
        <p>共 <strong>{{ processStatus.total }}</strong> 张照片</p>
        <p>建议淘汰: <strong>{{ processStatus.rejected_count }}</strong> 张</p>
        <p>识别 <strong>{{ processStatus.groups_count }}</strong> 个场景</p>
      </div>
      <button class="next-btn" @click="$router.push('/prescreen')">开始筛选 →</button>
    </div>

    <!-- Phase 4: Stopped -->
    <div v-if="phase === 'stopped'" class="done">
      <h3>⏹ 已停止</h3>
      <p>已处理 {{ processStatus.done }} 张，建议淘汰 {{ processStatus.rejected_count }} 张</p>
      <button class="next-btn" @click="$router.push('/prescreen')">开始筛选 →</button>
      <button class="restart-btn" @click="phase = 'select'">重新开始</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const phase = ref('select')
const currentPath = ref('')
const parentPath = ref('')
const dirs = ref([])
const preview = ref(null)
const runtime = ref('auto')
const filterLevel = ref('60')
const processStatus = ref({ done: 0, total: 0, rejected_count: 0, groups_count: 0, events: [] })
let pollHandle = null
let startTime = 0

const progressPct = computed(() => {
  if (!processStatus.value.total) return 0
  return Math.round(processStatus.value.done / processStatus.value.total * 100)
})

const recentEvents = computed(() => processStatus.value.events.slice(-40))

const eta = computed(() => {
  if (!processStatus.value.done || !startTime) return ''
  const elapsed = (Date.now() - startTime) / 1000
  const perPhoto = elapsed / processStatus.value.done
  const remaining = perPhoto * (processStatus.value.total - processStatus.value.done)
  if (remaining < 60) return `${Math.round(remaining)}秒`
  return `${Math.round(remaining / 60)}分钟`
})

async function browse(path = '') {
  try {
    const res = await axios.get('/api/browse', { params: { path } })
    currentPath.value = res.data.current
    parentPath.value = res.data.parent
    dirs.value = res.data.dirs
    preview.value = null
    if (currentPath.value) {
      try {
        const pv = await axios.post('/api/preview_folder', null, { params: { folder_path: currentPath.value } })
        preview.value = pv.data
      } catch {}
    }
  } catch (e) { alert('无法读取目录: ' + e.message) }
}

function navigate(path) { browse(path) }
function goUp() { if (parentPath.value) browse(parentPath.value) }

async function nativePick() {
  try {
    const res = await axios.post('/api/browse_folder')
    if (res.data.ok && res.data.folder) browse(res.data.folder)
  } catch (e) { alert('选择失败: ' + e.message) }
}

async function startProcess() {
  if (!currentPath.value) return
  phase.value = 'processing'
  startTime = Date.now()
  processStatus.value = { done: 0, total: 0, rejected_count: 0, groups_count: 0, events: [] }

  try {
    await axios.post('/api/auto_process', null, {
      params: { folder_path: currentPath.value, filter_level: parseInt(filterLevel.value), runtime: runtime.value }
    })
    startPolling()
  } catch (e) {
    alert('启动失败: ' + e.message)
    phase.value = 'select'
  }
}

function startPolling() {
  pollHandle = setInterval(async () => {
    try {
      const res = await axios.get('/api/auto_process/status')
      processStatus.value = res.data
      if (res.data.status === 'done') {
        clearInterval(pollHandle)
        phase.value = 'done'
      } else if (res.data.status === 'stopped') {
        clearInterval(pollHandle)
        phase.value = 'stopped'
      } else if (res.data.status === 'error') {
        clearInterval(pollHandle)
        alert('处理出错: ' + (res.data.error || '未知错误'))
        phase.value = 'select'
      }
    } catch {}
  }, 500)
}

async function stopProcess() {
  try {
    await axios.post('/api/auto_process/stop')
  } catch {}
}

onUnmounted(() => { if (pollHandle) clearInterval(pollHandle) })
onMounted(() => browse())

async function doReset() {
  if (!confirm('确定要重置吗？会清除所有缓存和进度数据。')) return
  try {
    await axios.post('/api/reset')
    location.reload(true)
  } catch (e) {
    alert('重置失败: ' + e.message)
  }
}
</script>

<style scoped>
.import-view { padding: 1.5rem 2rem; max-width: 800px; margin: 0 auto; }
.import-view h2 { margin-bottom: 1.5rem; text-align: center; }
.browser { background: #16213e; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
.browser-path { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.8rem; border-bottom: 1px solid #333; }
.path-label { color: #888; font-size: 0.85rem; }
.path-text { color: #eee; flex: 1; font-size: 0.9rem; word-break: break-all; }
.up-btn, .native-btn { padding: 0.3rem 0.8rem; background: #333; color: #aaa; border: none; border-radius: 6px; cursor: pointer; }
.up-btn:disabled { opacity: 0.3; }
.dir-list { max-height: 300px; overflow-y: auto; margin-bottom: 0.5rem; }
.dir-item { padding: 0.5rem 0.8rem; cursor: pointer; border-radius: 6px; }
.dir-item:hover { background: rgba(15,52,96,0.4); }
.empty { color: #666; padding: 1rem; text-align: center; }
.folder-preview { padding: 0.5rem; background: #0f3460; border-radius: 6px; text-align: center; }
.folder-preview strong { color: #4caf50; }
.options { background: #16213e; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
.option-group { margin-bottom: 0.8rem; }
.option-group > label { color: #aaa; font-size: 0.9rem; display: block; margin-bottom: 0.3rem; }
.radio-group { display: flex; gap: 1rem; }
.radio-group label { color: #eee; cursor: pointer; }
.start-btn { width: 100%; padding: 1rem; background: #0f3460; color: #fff; border: none; border-radius: 12px; font-size: 1.2rem; cursor: pointer; }
.start-btn:disabled { opacity: 0.5; }
.processing { }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.stop-btn { padding: 0.5rem 1.5rem; background: #c0392b; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
.stop-btn:hover { background: #e74c3c; }
.progress-bar { height: 8px; background: #333; border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #0f3460, #4caf50); transition: width 0.3s; }
.progress-info { display: flex; gap: 2rem; color: #888; font-size: 0.9rem; margin-bottom: 1rem; }
.photo-wall { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.5rem; max-height: 60vh; overflow-y: auto; }
.wall-cell { position: relative; border-radius: 6px; overflow: hidden; border: 2px solid transparent; animation: fadeIn 0.3s ease-out; }
.wall-cell.ok { border-color: #4caf50; }
.wall-cell.rejected { border-color: #c0392b; }
.wall-cell img { width: 100%; height: 80px; object-fit: cover; }
.wall-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 2px 4px; display: flex; justify-content: space-between; align-items: center; }
.wall-score { color: #fff; font-size: 0.7rem; }
.wall-reason { color: #ff9800; font-size: 0.65rem; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
.done { text-align: center; padding: 3rem 0; }
.done-stats { margin: 1rem 0; }
.done-stats strong { color: #4caf50; }
.next-btn { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; margin: 0.5rem; }
.restart-btn { padding: 0.8rem 2rem; background: #333; color: #aaa; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; margin: 0.5rem; }
.reset-section { margin-top: 2rem; text-align: center; padding: 1rem; border-top: 1px solid #333; }
.reset-btn { padding: 0.5rem 1.5rem; background: #c0392b; color: #fff; border: none; border-radius: 8px; cursor: pointer; }
.reset-btn:hover { background: #e74c3c; }
.reset-hint { color: #666; font-size: 0.8rem; margin-top: 0.5rem; }
</style>
