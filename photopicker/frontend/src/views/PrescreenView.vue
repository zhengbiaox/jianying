<template>
  <div class="prescreen-view">
    <h2>照片筛选</h2>
    <p class="summary">以下照片建议优化，确认后将进入选片环节</p>

    <div class="prescreen-stats">
      <span>待优化: {{ rejectedPhotos.length }} 张</span>
    </div>

    <div class="prescreen-grid">
      <div v-for="photo in rejectedPhotos" :key="photo.id"
           class="prescreen-card"
           @click="openPreview(photo.id)">
        <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
        <div class="card-info">
          <span class="score">{{ photo.score }}</span>
          <div class="reasons">
            <span v-for="r in getReasons(photo)" :key="r" class="reason-tag">{{ r }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="prescreen-actions">
      <button class="confirm-btn" @click="confirm">
        确认筛选，进入选片 →
      </button>
    </div>

    <div v-if="previewVisible" class="preview-overlay" @click.self="previewVisible = false">
      <img :src="'/api/preview/' + previewId" class="preview-img" />
      <button class="preview-close" @click="previewVisible = false">关闭</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const photos = ref([])
const previewVisible = ref(false)
const previewId = ref('')

const rejectedPhotos = computed(() => photos.value.filter(p => p.score < 60))

function getReasons(photo) {
  return photo.reasons && photo.reasons.length ? photo.reasons : ['画质有待提升']
}

function openPreview(id) {
  previewId.value = id
  previewVisible.value = true
}

async function confirm() {
  try {
    await axios.post('/api/prescreen/confirm')
    router.push('/pick')
  } catch (e) {
    alert('确认失败: ' + e.message)
  }
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

onMounted(loadPhotos)
</script>

<style scoped>
.prescreen-view { padding: 1.5rem 2rem; }
.prescreen-view h2 { margin-bottom: 0.5rem; }
.summary { color: #aaa; margin-bottom: 1rem; }
.prescreen-stats { display: flex; gap: 2rem; margin-bottom: 1rem; color: #888; }
.prescreen-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; max-height: 60vh; overflow-y: auto; }
.prescreen-card { background: #16213e; border-radius: 8px; overflow: hidden; border: 2px solid #c0392b; position: relative; cursor: pointer; }
.prescreen-card img { width: 100%; height: 120px; object-fit: cover; }
.card-info { padding: 0.5rem; }
.score { background: #c0392b; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.reasons { margin-top: 0.3rem; display: flex; gap: 0.3rem; flex-wrap: wrap; }
.reason-tag { background: #333; color: #ff9800; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }
.prescreen-actions { text-align: center; margin-top: 1.5rem; }
.confirm-btn { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.preview-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.95); z-index: 1000; display: flex; align-items: center; justify-content: center; flex-direction: column; }
.preview-img { max-width: 90vw; max-height: 85vh; object-fit: contain; border-radius: 8px; }
.preview-close { margin-top: 1rem; padding: 0.5rem 2rem; background: #333; color: #aaa; border: none; border-radius: 8px; cursor: pointer; }
</style>
