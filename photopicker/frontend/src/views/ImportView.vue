<template>
  <div class="import-view">
    <h2>选择照片文件夹</h2>

    <div class="browser">
      <div class="browser-path">
        <span class="path-label">当前路径:</span>
        <span class="path-text">{{ currentPath }}</span>
        <button class="up-btn" @click="goUp" :disabled="!parentPath">↑ 上级</button>
        <button class="native-btn" @click="nativePickFolder">系统选择</button>
      </div>

      <div v-if="folderPreview" class="folder-preview">
        发现 {{ folderPreview.count }} 张照片，共 {{ folderPreview.size_mb }} MB
      </div>

      <div class="dir-list">
        <div
          v-for="dir in dirs"
          :key="dir.path"
          class="dir-item"
          @click="navigate(dir.path)"
        >
          📁 {{ dir.name }}
        </div>
        <div v-if="dirs.length === 0" class="empty">此目录下没有子文件夹</div>
      </div>

      <button class="select-btn" @click="importCurrent">
        选择此文件夹 ({{ currentPath }})
      </button>
    </div>

    <div v-if="resumeSession" class="resume-banner">
      <p>发现未完成的选片任务（{{ resumeSession.total_groups }}组，已完成{{ resumeSession.current_group }}组），是否继续？</p>
      <button class="resume-btn" @click="resumeTask">继续上次</button>
      <button class="dismiss-btn" @click="resumeSession = null">忽略</button>
    </div>

    <div v-if="importing" class="progress">
      <p>正在扫描... 已发现 {{ count }} 张照片</p>
    </div>

    <div v-if="done" class="done">
      <p>✅ 导入完成，共 {{ count }} 张照片</p>
      <button @click="$router.push('/filter')">开始初筛 →</button>
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
const importing = ref(false)
const done = ref(false)
const count = ref(0)
const resumeSession = ref(null)
const folderPreview = ref(null)

async function browse(path = '') {
  try {
    const res = await axios.get('/api/browse', { params: { path } })
    currentPath.value = res.data.current
    parentPath.value = res.data.parent
    dirs.value = res.data.dirs
    previewFolder(res.data.current)
  } catch (e) {
    alert('无法读取目录: ' + e.message)
  }
}

async function previewFolder(path) {
  try {
    const res = await axios.post('/api/preview_folder', null, { params: { folder_path: path } })
    folderPreview.value = res.data
  } catch (e) {
    folderPreview.value = null
  }
}

function navigate(path) {
  browse(path)
}

function goUp() {
  if (parentPath.value) {
    browse(parentPath.value)
  }
}

async function nativePickFolder() {
  try {
    const res = await axios.post('/api/browse_folder')
    if (res.data.error) {
      alert('系统选择失败: ' + res.data.error)
      return
    }
    if (res.data.cancelled) {
      return
    }
    browse(res.data.folder)
  } catch (e) {
    alert('系统选择失败: ' + e.message)
  }
}

async function importCurrent() {
  importing.value = true
  done.value = false
  try {
    const res = await axios.post('/api/import', null, {
      params: { folder_path: currentPath.value }
    })
    count.value = res.data.count
    done.value = true
  } catch (e) {
    alert('导入失败: ' + e.message)
  } finally {
    importing.value = false
  }
}

async function checkSession() {
  try {
    const res = await axios.get('/api/state')
    if (res.data.has_session) {
      resumeSession.value = res.data
    }
  } catch (e) {
    // no session or error, ignore
  }
}

async function resumeTask() {
  try {
    await axios.post('/api/state/resume', { folder_path: currentPath.value || resumeSession.value.folder_path || '' })
    router.push('/filter')
  } catch (e) {
    alert('恢复失败: ' + e.message)
  }
}

onMounted(() => {
  browse()
  checkSession()
})
</script>

<style scoped>
.import-view { padding: 1.5rem 2rem; max-width: 700px; margin: 0 auto; }
.import-view h2 { margin-bottom: 1.5rem; }
.browser { background: #16213e; border-radius: 12px; padding: 1rem; }
.browser-path { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.8rem; border-bottom: 1px solid #333; }
.path-label { color: #888; font-size: 0.85rem; }
.path-text { color: #eee; flex: 1; font-size: 0.9rem; word-break: break-all; }
.up-btn { padding: 0.3rem 0.8rem; background: #333; color: #aaa; border: none; border-radius: 6px; cursor: pointer; }
.up-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.native-btn { padding: 0.3rem 0.8rem; background: #0f3460; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.native-btn:hover { background: #1a5276; }
.folder-preview { padding: 0.6rem 1rem; background: #0a1628; border-radius: 8px; color: #4caf50; font-size: 0.9rem; margin-bottom: 1rem; }
.dir-list { max-height: 400px; overflow-y: auto; margin-bottom: 1rem; }
.dir-item { padding: 0.5rem 0.8rem; cursor: pointer; border-radius: 6px; transition: background 0.15s; }
.dir-item:hover { background: rgba(15,52,96,0.4); }
.empty { color: #666; padding: 1rem; text-align: center; }
.select-btn { width: 100%; padding: 0.8rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
.select-btn:hover { background: #1a5276; }
.done { margin-top: 2rem; text-align: center; background: #16213e; padding: 1.5rem; border-radius: 12px; }
.done button { margin-top: 1rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.progress { margin-top: 1.5rem; text-align: center; color: #aaa; }
.resume-banner { margin-top: 1.5rem; padding: 1rem 1.5rem; background: #2d1b00; border: 1px solid #ff9800; border-radius: 12px; display: flex; align-items: center; gap: 1rem; }
.resume-banner p { flex: 1; color: #ffcc80; margin: 0; }
.resume-btn { padding: 0.5rem 1.2rem; background: #ff9800; color: #000; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.dismiss-btn { padding: 0.5rem 1.2rem; background: #333; color: #aaa; border: none; border-radius: 6px; cursor: pointer; }
</style>
