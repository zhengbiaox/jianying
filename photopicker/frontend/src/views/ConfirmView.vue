<template>
  <div class="confirm-view">
    <ProgressSteps :current="3" />
    <div class="content">
    <h2>确认导出</h2>

    <!-- PK not complete -->
    <div v-if="!pkComplete" class="not-ready">
      <p class="not-ready-msg">尚有未完成的PK</p>
      <p class="not-ready-info">
        已完成 {{ pkStatus.finished_groups }} / {{ pkStatus.total_groups }} 个场景
      </p>
      <p class="not-ready-info">
        已保留 {{ pkStatus.selected_count }} 张
      </p>
      <button class="go-pick-btn" @click="$router.push('/pick')">继续PK →</button>
    </div>

    <!-- PK complete -->
    <div v-else>
      <div class="confirm-stats">
        <span>已选 <strong>{{ selectedPhotos.length }}</strong> 张</span>
        <span>暂存 <strong>{{ heldPhotos.length }}</strong> 张</span>
        <span>已淘汰 <strong>{{ rejectedCount }}</strong> 张</span>
      </div>

      <!-- Person naming -->
      <div v-if="persons.length > 0" class="section persons-section">
        <h3>人物命名</h3>
        <p class="section-hint">给检测到的人物起个名字，导出时会按人物分文件夹</p>
        <div class="persons-list">
          <div v-for="person in persons" :key="person.id" class="person-row">
            <div class="person-photos">
              <img
                v-for="(photoId, idx) in person.sample_photos.slice(0, 3)"
                :key="idx"
                :src="'/api/thumbnail/' + photoId"
                class="person-thumb"
              />
            </div>
            <input
              class="person-name-input"
              :value="person.name"
              @change="namePerson(person.id, $event.target.value)"
              placeholder="输入名字..."
            />
            <span class="person-count">{{ person.count }} 张</span>
          </div>
        </div>
      </div>

      <!-- Selected photos -->
      <div class="section">
        <h3>已选照片 ({{ selectedPhotos.length }})</h3>
        <div class="photo-grid">
          <div v-for="photo in selectedPhotos" :key="photo.id" class="photo-card selected">
            <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
            <span class="card-score">{{ photo.score }}</span>
          </div>
        </div>
      </div>

      <!-- Held photos -->
      <div v-if="heldPhotos.length > 0" class="section held-section">
        <h3>暂存照片 ({{ heldPhotos.length }})</h3>
        <div class="held-actions">
          <button class="action-btn accept" @click="batchHoldAction('accept')">全部入选</button>
          <button class="action-btn reject" @click="batchHoldAction('reject')">全部淘汰</button>
        </div>
        <div class="photo-grid">
          <div v-for="photo in heldPhotos" :key="photo.id" class="photo-card held">
            <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
            <span class="card-score">{{ photo.score }}</span>
            <div class="card-actions">
              <button class="mini-btn accept" @click="handleHeldPhoto(photo.id, 'accept')">入选</button>
              <button class="mini-btn reject" @click="handleHeldPhoto(photo.id, 'reject')">淘汰</button>
            </div>
          </div>
        </div>
      </div>

      <div class="confirm-actions">
        <div class="mode-select">
          <label>导出模式:</label>
          <label><input type="radio" v-model="mode" value="copy" /> 复制 · 保留原件</label>
          <label><input type="radio" v-model="mode" value="move" /> 移动 · 节省空间</label>
        </div>
        <div class="group-select" v-if="persons.length > 0">
          <label>分组方式:</label>
          <label><input type="radio" v-model="groupBy" value="none" /> 全部放一起</label>
          <label><input type="radio" v-model="groupBy" value="person" /> 按人物分文件夹</label>
          <label><input type="radio" v-model="groupBy" value="scene" /> 按场景分文件夹</label>
        </div>
        <button class="export-btn" @click="doExport" :disabled="exporting || selectedPhotos.length === 0">
          {{ exporting ? '导出中...' : '导出并归档' }}
        </button>
      </div>

      <div v-if="exportResult" class="export-result">
        <p>✅ 归档完成！</p>
        <template v-if="exportResult.folders">
          <div v-for="(count, name) in exportResult.folders" :key="name" class="folder-info">
            <span class="folder-name">{{ name }}</span>
            <span class="folder-count">{{ count }} 张</span>
          </div>
        </template>
        <template v-else>
          <p>入选 {{ exportResult['入选'] }} 张</p>
          <p>淘汰 {{ exportResult['未入选'] }} 张</p>
        </template>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import ProgressSteps from '../components/ProgressSteps.vue'

const router = useRouter()
const allPhotos = ref([])
const pkStatus = ref({ complete: false, total_groups: 0, finished_groups: 0, selected_count: 0 })
const persons = ref([])
const mode = ref('copy')
const groupBy = ref('none')
const exporting = ref(false)
const exportResult = ref(null)

const pkComplete = computed(() => pkStatus.value.complete)
const selectedPhotos = computed(() => allPhotos.value.filter(p => p.is_selected))
const heldPhotos = computed(() => allPhotos.value.filter(p => p.is_pending))
const rejectedCount = computed(() => allPhotos.value.filter(p => p.is_rejected).length)

async function loadStatus() {
  try {
    const res = await axios.get('/api/pk/status')
    pkStatus.value = res.data
  } catch {}
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  allPhotos.value = res.data
}

async function loadPersons() {
  try {
    const res = await axios.get('/api/persons')
    persons.value = res.data
  } catch {}
}

async function namePerson(personId, name) {
  try {
    await axios.post(`/api/persons/${personId}/name`, null, {
      params: { name }
    })
    await loadPersons()
  } catch (e) {
    alert('命名失败: ' + e.message)
  }
}

async function handleHeldPhoto(photoId, action) {
  try {
    if (action === 'accept') {
      await axios.post(`/api/photos/${photoId}/select`)
    } else {
      await axios.post(`/api/photos/${photoId}/reject`)
    }
    await loadPhotos()
  } catch (e) {
    alert('操作失败: ' + e.message)
  }
}

async function batchHoldAction(action) {
  try {
    for (const photo of heldPhotos.value) {
      if (action === 'accept') {
        await axios.post(`/api/photos/${photo.id}/select`)
      } else {
        await axios.post(`/api/photos/${photo.id}/reject`)
      }
    }
    await loadPhotos()
  } catch (e) {
    alert('操作失败: ' + e.message)
  }
}

async function doExport() {
  exporting.value = true
  try {
    const res = await axios.post('/api/export/final', null, {
      params: { mode: mode.value, group_by: groupBy.value }
    })
    exportResult.value = res.data
  } catch (e) {
    alert('导出失败: ' + e.message)
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadPhotos()
  loadPersons()
})
</script>

<style scoped>
.confirm-view { padding: 1.5rem 2rem; }
.confirm-view h2 { margin-bottom: 1rem; text-align: center; }
.not-ready { text-align: center; padding: 5rem 0; }
.not-ready-msg { font-size: 1.5rem; color: #ff9800; margin-bottom: 1rem; }
.not-ready-info { color: #888; margin-bottom: 0.5rem; font-size: 1.1rem; }
.go-pick-btn { margin-top: 2rem; padding: 1rem 2.5rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.2rem; cursor: pointer; }
.confirm-stats { display: flex; gap: 3rem; justify-content: center; margin-bottom: 2rem; font-size: 1.1rem; }
.confirm-stats strong { color: #4caf50; }
.section { margin-bottom: 2rem; }
.section h3 { color: #aaa; font-size: 1.1rem; margin-bottom: 0.8rem; }
.section-hint { color: #666; font-size: 0.85rem; margin-bottom: 1rem; }
.persons-section { background: #16213e; padding: 1.5rem; border-radius: 12px; }
.persons-list { display: flex; flex-direction: column; gap: 1rem; }
.person-row { display: flex; align-items: center; gap: 1rem; }
.person-photos { display: flex; gap: 6px; }
.person-thumb { width: 50px; height: 50px; border-radius: 8px; object-fit: cover; border: 2px solid #4cc9f0; }
.person-name-input { flex: 1; padding: 0.6rem 0.8rem; background: #1a1a2e; border: 1px solid #333; border-radius: 8px; color: #fff; font-size: 1rem; }
.person-name-input:focus { outline: none; border-color: #4cc9f0; }
.person-count { color: #888; font-size: 0.9rem; width: 60px; text-align: right; }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.8rem; max-height: 50vh; overflow-y: auto; }
.photo-card { position: relative; border-radius: 10px; overflow: hidden; }
.photo-card.selected { border: 2px solid #4caf50; }
.photo-card.held { border: 2px solid #f39c12; }
.photo-card img { width: 100%; height: 120px; object-fit: cover; }
.card-score { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,0.7); color: #4caf50; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; }
.card-actions { position: absolute; bottom: 6px; left: 6px; display: flex; gap: 6px; }
.mini-btn { padding: 4px 8px; border: none; border-radius: 4px; font-size: 0.75rem; cursor: pointer; }
.mini-btn.accept { background: #4caf50; color: #fff; }
.mini-btn.reject { background: #e74c3c; color: #fff; }
.held-section { background: #16213e; padding: 1.5rem; border-radius: 12px; }
.held-actions { display: flex; gap: 0.8rem; margin-bottom: 1rem; }
.action-btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; font-size: 0.9rem; cursor: pointer; }
.action-btn.accept { background: #4caf50; color: #fff; }
.action-btn.reject { background: #e74c3c; color: #fff; }
.confirm-actions { text-align: center; margin-top: 2rem; }
.mode-select, .group-select { display: flex; gap: 1.5rem; align-items: center; justify-content: center; margin-bottom: 1.2rem; }
.mode-select label, .group-select label { color: #aaa; cursor: pointer; font-size: 1rem; }
.export-btn { padding: 1rem 2.5rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.2rem; cursor: pointer; }
.export-btn:disabled { opacity: 0.5; }
.export-result { text-align: center; margin-top: 2rem; background: #16213e; padding: 2rem; border-radius: 12px; }
.folder-info { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #333; font-size: 1rem; }
.folder-name { color: #aaa; }
.folder-count { color: #4caf50; }
</style>
