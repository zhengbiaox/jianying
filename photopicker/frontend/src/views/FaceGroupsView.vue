<template>
  <div class="face-groups-view">
    <h2>按人物</h2>
    <p class="summary">以下照片按人物自动分组</p>

    <div v-if="faceGroups.length === 0" class="empty-state">
      <p>暂无人物分组</p>
      <p class="hint">InsightFace 模型加载后可自动识别照片中的人物</p>
    </div>

    <div v-else class="face-groups-grid">
      <div v-for="group in faceGroups" :key="group.id" class="face-group-card">
        <div class="group-header">
          <span class="group-label">{{ group.label || '人物' }}</span>
          <span class="group-count">{{ group.photos.length }} 张</span>
        </div>
        <div class="group-photos">
          <div v-for="photoId in group.photos.slice(0, 9)" :key="photoId" class="photo-thumb"
               @click="openPreview(photoId)">
            <img :src="'/api/thumbnail/' + photoId" loading="lazy" />
          </div>
          <div v-if="group.photos.length > 9" class="photo-more">
            +{{ group.photos.length - 9 }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="previewVisible" class="preview-overlay" @click.self="previewVisible = false">
      <img :src="'/api/preview/' + previewId" class="preview-img" />
      <button class="preview-close" @click="previewVisible = false">关闭</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const faceGroups = ref([])
const previewVisible = ref(false)
const previewId = ref('')

function openPreview(id) {
  previewId.value = id
  previewVisible.value = true
}

onMounted(async () => {
  try {
    const res = await axios.get('/api/face_groups')
    faceGroups.value = res.data.map((g, i) => ({
      ...g,
      label: `人物 ${i + 1}`
    }))
  } catch (e) {
    console.error('Failed to load face groups', e)
  }
})
</script>

<style scoped>
.face-groups-view {
  padding: 2rem;
}
h2 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}
.summary {
  color: #aaa;
  margin-bottom: 2rem;
}
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #888;
}
.hint {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  color: #666;
}
.face-groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}
.face-group-card {
  background: #16213e;
  border-radius: 12px;
  padding: 1rem;
}
.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.group-label {
  font-weight: 600;
  font-size: 1.1rem;
}
.group-count {
  color: #aaa;
  font-size: 0.9rem;
}
.group-photos {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}
.photo-thumb {
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}
.photo-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.photo-thumb:hover img {
  opacity: 0.8;
}
.photo-more {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f3460;
  border-radius: 8px;
  font-size: 1.2rem;
  color: #aaa;
}
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.preview-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
}
.preview-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
}
</style>
