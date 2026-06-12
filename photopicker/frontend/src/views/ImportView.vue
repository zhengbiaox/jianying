<template>
  <div class="import-view">
    <h2>PhotoPicker 选片工具</h2>

    <div class="browser">
      <div class="browser-path">
        <span class="path-label">当前路径:</span>
        <span class="path-text">{{ currentPath }}</span>
        <button class="up-btn" @click="goUp" :disabled="!parentPath">↑ 上级</button>
        <button class="native-btn" @click="nativePick">系统选择</button>
      </div>
      <div class="dir-list">
        <div v-for="dir in dirs" :key="dir.path" class="dir-item" @click="navigate(dir.path)">
          📁 {{ dir.name }}
        </div>
        <div v-if="dirs.length === 0" class="empty">此目录下没有子文件夹</div>
      </div>
      <div class="folder-preview" v-if="preview">
        <p>发现 <strong>{{ preview.count }}</strong> 张照片，共 <strong>{{ preview.size_mb }} MB</strong></p>
      </div>
      <button class="select-btn" @click="importCurrent">
        选择此文件夹
      </button>
    </div>

    <div class="options">
      <div class="option-group">
        <label>加速方式:</label>
        <div class="radio-group">
          <label><input type="radio" v-model="runtime" value="auto" /> 自动</label>
          <label><input type="radio" v-model="runtime" value="cpu" /> CPU</label>
          <label><input type="radio" v-model="runtime" value="gpu" /> GPU</label>
        </div>
      </div>
      <div class="option-group">
        <label>筛选模式:</label>
        <div class="radio-group">
          <label><input type="radio" v-model="filterLevel" value="80" /> 🟢 严格</label>
          <label><input type="radio" v-model="filterLevel" value="60" /> 🟡 适中</label>
          <label><input type="radio" v-model="filterLevel" value="40" /> 🔴 宽松</label>
        </div>
      </div>
    </div>

    <button class="start-btn" @click="startProcess" :disabled="processing || !currentPath">
      {{ processing ? '处理中...' : '开始整理' }}
    </button>

    <div v-if="processing" class="progress">
      <p>正在分析照片质量和分组，请稍候...</p>
    </div>

    <div v-if="result" class="result">
      <p>✅ 分析完成！共 {{ result.total }} 张照片</p>
      <p>废片: {{ result.rejected_count }} 张 | 分组: {{ result.groups_count }} 组</p>
      <button @click="$router.push('/prescreen')">进入废片审核 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const currentPath = ref('')
const parentPath = ref('')
const dirs = ref([])
const preview = ref(null)
const runtime = ref('auto')
const filterLevel = ref('60')
const processing = ref(false)
const result = ref(null)

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
  } catch (e) {
    alert('无法读取目录: ' + e.message)
  }
}

function navigate(path) { browse(path) }
function goUp() { if (parentPath.value) browse(parentPath.value) }

async function nativePick() {
  try {
    const res = await axios.post('/api/browse_folder')
    if (res.data.ok && res.data.folder) {
      browse(res.data.folder)
    }
  } catch (e) {
    alert('选择失败: ' + e.message)
  }
}

function importCurrent() {
  // Just select, don't process yet
}

async function startProcess() {
  if (!currentPath.value) return
  processing.value = true
  result.value = null
  try {
    const res = await axios.post('/api/auto_process', null, {
      params: {
        folder_path: currentPath.value,
        filter_level: parseInt(filterLevel.value),
        runtime: runtime.value,
      }
    })
    result.value = res.data
  } catch (e) {
    alert('处理失败: ' + e.message)
  } finally {
    processing.value = false
  }
}

onMounted(() => browse())
</script>

<style scoped>
.import-view { padding: 1.5rem 2rem; max-width: 700px; margin: 0 auto; }
.import-view h2 { margin-bottom: 1.5rem; text-align: center; }
.browser { background: #16213e; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
.browser-path { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.8rem; border-bottom: 1px solid #333; }
.path-label { color: #888; font-size: 0.85rem; }
.path-text { color: #eee; flex: 1; font-size: 0.9rem; word-break: break-all; }
.up-btn, .native-btn { padding: 0.3rem 0.8rem; background: #333; color: #aaa; border: none; border-radius: 6px; cursor: pointer; }
.up-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.dir-list { max-height: 300px; overflow-y: auto; margin-bottom: 0.5rem; }
.dir-item { padding: 0.5rem 0.8rem; cursor: pointer; border-radius: 6px; transition: background 0.15s; }
.dir-item:hover { background: rgba(15,52,96,0.4); }
.empty { color: #666; padding: 1rem; text-align: center; }
.folder-preview { padding: 0.5rem; background: #0f3460; border-radius: 6px; margin-bottom: 0.5rem; text-align: center; }
.folder-preview strong { color: #4caf50; }
.select-btn { width: 100%; padding: 0.6rem; background: #333; color: #aaa; border: none; border-radius: 8px; cursor: pointer; margin-bottom: 1rem; }
.options { background: #16213e; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
.option-group { margin-bottom: 0.8rem; }
.option-group label { color: #aaa; font-size: 0.9rem; display: block; margin-bottom: 0.3rem; }
.radio-group { display: flex; gap: 1rem; }
.radio-group label { color: #eee; cursor: pointer; display: flex; align-items: center; gap: 0.3rem; }
.start-btn { width: 100%; padding: 1rem; background: #0f3460; color: #fff; border: none; border-radius: 12px; font-size: 1.2rem; cursor: pointer; }
.start-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.start-btn:hover:not(:disabled) { background: #1a5276; }
.progress { text-align: center; margin-top: 1rem; color: #aaa; }
.result { text-align: center; margin-top: 1.5rem; background: #16213e; padding: 1.5rem; border-radius: 12px; }
.result button { margin-top: 1rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
</style>
