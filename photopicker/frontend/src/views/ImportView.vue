<template>
  <div class="import-view">
    <a-card title="选择照片目录" :bordered="false" style="background: #16213e;">
      <div class="browser-path">
        <a-space>
          <a-button @click="goUp" :disabled="!parentPath">↑ 上级</a-button>
          <a-button @click="nativePick">浏览</a-button>
        </a-space>
        <a-typography-text :copyable="true" style="color: #eee; margin-left: 1rem;">{{ currentPath }}</a-typography-text>
      </div>
      
      <a-scrollbar style="max-height: 300px; overflow-y: auto;">
        <a-list :data="dirs" :bordered="false">
          <template #item="{ item }">
            <a-list-item @click="navigate(item.path)" style="cursor: pointer;">
              📁 {{ item.name }}
            </a-list-item>
          </template>
        </a-list>
      </a-scrollbar>
      
      <a-alert v-if="preview" type="info" style="margin: 1rem 0;">
        已识别 <strong>{{ preview.count }}</strong> 张照片，共 <strong>{{ preview.size_mb }} MB</strong>
      </a-alert>
    </a-card>
    
    <a-card title="处理选项" :bordered="false" style="background: #16213e; margin-top: 1rem;">
      <a-form :model="{}" layout="horizontal">
        <a-form-item label="处理引擎">
          <a-radio-group v-model="runtime">
            <a-radio value="auto">自动检测</a-radio>
            <a-radio value="cpu">CPU</a-radio>
            <a-radio value="gpu">GPU</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="甄选策略">
          <a-radio-group v-model="filterLevel">
            <a-radio value="80">精选 · 严格</a-radio>
            <a-radio value="60">均衡 · 推荐</a-radio>
            <a-radio value="40">宽泛 · 保守</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-card>
    
    <a-button type="primary" size="large" long :disabled="!currentPath" :loading="processing" @click="startProcess" style="margin-top: 1rem;">
      {{ processing ? '正在逐帧分析...' : '开始分析' }}
    </a-button>
    
    <a-card v-if="processing" style="margin-top: 1rem; background: #16213e;">
      <a-progress :percent="progressPct" :show-text="true" status="normal" />
      <a-space style="margin-top: 0.5rem;">
        <a-tag color="blue">{{ processStatus.done }} / {{ processStatus.total }}</a-tag>
        <a-tag color="orange">建议淘汰 {{ processStatus.rejected_count }} 张</a-tag>
        <a-tag color="green" v-if="eta">预计剩余 {{ eta }}</a-tag>
      </a-space>
      <a-button type="outline" status="danger" @click="stopProcess" style="margin-top: 0.5rem;">停止</a-button>
      
      <div class="photo-wall">
        <div v-for="ev in recentEvents" :key="ev.id" class="wall-cell" :class="{ rejected: ev.rejected, ok: !ev.rejected }">
          <img :src="'/api/thumbnail/' + ev.id" loading="lazy" />
          <div class="wall-overlay">
            <a-tag :color="ev.rejected ? 'red' : 'green'" size="small">{{ ev.score }}</a-tag>
            <a-tag v-if="ev.rejected" color="orange" size="small">{{ ev.reasons[0] || '' }}</a-tag>
          </div>
        </div>
      </div>
    </a-card>
    
    <a-result v-if="result" status="success" title="分析完成" style="margin-top: 1rem;">
      <template #subtitle>
        <p>共 {{ result.total }} 张照片</p>
        <p>建议淘汰 {{ result.rejected_count }} 张 · 识别 {{ result.groups_count }} 个场景</p>
      </template>
      <template #extra>
        <a-button type="primary" @click="$router.push('/prescreen')">开始筛选 →</a-button>
      </template>
    </a-result>
    
    <a-result v-if="stopped" status="warning" title="已停止" style="margin-top: 1rem;">
      <template #subtitle>
        <p>已处理 {{ processStatus.done }} 张，建议淘汰 {{ processStatus.rejected_count }} 张</p>
      </template>
      <template #extra>
        <a-space>
          <a-button type="primary" @click="$router.push('/prescreen')">进入筛选 →</a-button>
          <a-button @click="phase = 'select'">重新开始</a-button>
        </a-space>
      </template>
    </a-result>
    
    <a-divider />
    <div class="reset-section">
      <a-button type="text" status="danger" @click="doReset">重新开始</a-button>
      <a-typography-text type="secondary" style="font-size: 0.8rem;">清除所有缓存与进度</a-typography-text>
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
const processing = ref(false)
const stopped = ref(false)
const result = ref(null)
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
  } catch (e) { console.error(e) }
}

function navigate(path) { browse(path) }
function goUp() { if (parentPath.value) browse(parentPath.value) }

async function nativePick() {
  try {
    const res = await axios.post('/api/browse_folder')
    if (res.data.ok && res.data.folder) browse(res.data.folder)
  } catch {}
}

async function startProcess() {
  if (!currentPath.value) return
  processing.value = true
  stopped.value = false
  result.value = null
  startTime = Date.now()
  processStatus.value = { done: 0, total: 0, rejected_count: 0, groups_count: 0, events: [] }
  try {
    await axios.post('/api/auto_process', null, {
      params: { folder_path: currentPath.value, filter_level: parseInt(filterLevel.value), runtime: runtime.value }
    })
    startPolling()
  } catch (e) {
    processing.value = false
  }
}

function startPolling() {
  pollHandle = setInterval(async () => {
    try {
      const res = await axios.get('/api/auto_process/status')
      processStatus.value = res.data
      if (res.data.status === 'done') {
        clearInterval(pollHandle)
        processing.value = false
        result.value = { total: processStatus.value.total, rejected_count: processStatus.value.rejected_count, groups_count: processStatus.value.groups_count }
      } else if (res.data.status === 'stopped') {
        clearInterval(pollHandle)
        processing.value = false
        stopped.value = true
      } else if (res.data.status === 'error') {
        clearInterval(pollHandle)
        processing.value = false
      }
    } catch {}
  }, 500)
}

async function stopProcess() {
  try { await axios.post('/api/auto_process/stop') } catch {}
}

async function doReset() {
  try {
    await axios.post('/api/reset')
    location.reload(true)
  } catch {}
}

onUnmounted(() => { if (pollHandle) clearInterval(pollHandle) })
onMounted(() => browse())
</script>

<style scoped>
.import-view { padding: 1.5rem 2rem; max-width: 700px; margin: 0 auto; }
.browser-path { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
.photo-wall { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.5rem; max-height: 300px; overflow-y: auto; margin-top: 1rem; }
.wall-cell { position: relative; border-radius: 6px; overflow: hidden; border: 2px solid transparent; animation: fadeIn 0.3s ease-out; }
.wall-cell.ok { border-color: #4caf50; }
.wall-cell.rejected { border-color: #c0392b; }
.wall-cell img { width: 100%; height: 60px; object-fit: cover; }
.wall-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 2px; display: flex; gap: 2px; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
.reset-section { text-align: center; }
</style>
