<template>
  <div class="export-view">
    <h2>导出选中照片</h2>

    <div class="export-form">
      <label>输出目录:</label>
      <input v-model="outputDir" placeholder="如: /Users/xxx/Photos/selected" />

      <label>文件夹名称:</label>
      <input v-model="folderName" placeholder="如: best_photos" />

      <p class="summary">已选 {{ selectedPhotos.length }} 张照片</p>

      <button @click="doExport" :disabled="exporting || selectedPhotos.length === 0">
        {{ exporting ? '导出中...' : '开始导出' }}
      </button>
    </div>

    <div v-if="exportResult" class="export-result">
      <p>✅ 导出完成</p>
      <p>复制: {{ exportResult.copied }} 张</p>
      <p>跳过: {{ exportResult.skipped }} 张</p>
      <p>目录: {{ exportResult.output_dir }}</p>
    </div>

    <div class="selected-list">
      <h3>已选照片</h3>
      <div class="selected-grid">
        <div v-for="photo in selectedPhotos" :key="photo.id" class="selected-thumb">
          <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
          <button class="remove-btn" @click="removePhoto(photo.id)">✕</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const photos = ref([])
const outputDir = ref('')
const folderName = ref('selected_photos')
const exporting = ref(false)
const exportResult = ref(null)

const selectedPhotos = computed(() => photos.value.filter(p => p.is_selected))

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

async function removePhoto(id) {
  await axios.post(`/api/photos/${id}/reject`)
  await loadPhotos()
}

async function doExport() {
  if (!outputDir.value || !folderName.value) {
    alert('请填写输出目录和文件夹名称')
    return
  }

  exporting.value = true
  try {
    const res = await axios.post('/api/export', {
      photo_ids: selectedPhotos.value.map(p => p.id),
      output_dir: outputDir.value,
      folder_name: folderName.value,
    })
    exportResult.value = res.data
  } catch (e) {
    alert('导出失败: ' + e.message)
  } finally {
    exporting.value = false
  }
}

onMounted(loadPhotos)
</script>

<style scoped>
.export-view { padding: 1.5rem 2rem; }
.export-form { max-width: 500px; margin: 2rem auto; display: flex; flex-direction: column; gap: 0.8rem; }
.export-form label { color: #aaa; font-size: 0.9rem; }
.export-form input { padding: 0.6rem 1rem; background: #16213e; border: 1px solid #333; border-radius: 6px; color: #fff; font-size: 0.95rem; }
.summary { color: #4caf50; font-size: 1.1rem; margin-top: 0.5rem; }
.export-form button { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 1rem; }
.export-form button:disabled { opacity: 0.5; }
.export-result { text-align: center; margin: 2rem 0; padding: 1.5rem; background: #16213e; border-radius: 8px; }
.selected-list { margin-top: 2rem; }
.selected-list h3 { margin-bottom: 1rem; color: #aaa; }
.selected-grid { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.selected-thumb { position: relative; width: 100px; height: 100px; border-radius: 6px; overflow: hidden; border: 2px solid #4caf50; }
.selected-thumb img { width: 100%; height: 100%; object-fit: cover; }
.remove-btn { position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.7); color: #fff; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 0.7rem; }
</style>
