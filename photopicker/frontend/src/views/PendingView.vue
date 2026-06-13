<template>
  <div class="pending-view">
    <h2>权衡 · 待定审阅</h2>
    <p class="summary">以下照片暂缓决定，请逐张审阅</p>

    <div class="pending-stats">
      <span>待审: {{ pendingPhotos.length }} 张</span>
      <span>已保留: {{ selectedCount }} 张</span>
      <span>已放弃: {{ rejectedCount }} 张</span>
    </div>

    <div v-if="pendingPhotos.length > 0" class="pending-area">
      <div class="pending-card">
        <img :src="'/api/preview/' + currentPhoto.id" class="pending-img" />
        <div class="pending-info">
          <span class="pending-score">评分: {{ currentPhoto.score }}</span>
          <span class="pending-name">{{ currentPhoto.path?.split('/').pop() }}</span>
        </div>
        <div class="pending-actions">
          <button class="select-btn" @click="decide(currentPhoto.id, 'select')">保留</button>
          <button class="reject-btn" @click="decide(currentPhoto.id, 'reject')">放弃</button>
        </div>
        <div class="pending-nav">
          <span>{{ currentIndex + 1 }} / {{ pendingPhotos.length }}</span>
        </div>
      </div>
    </div>

    <div v-else class="pending-done">
      <p>所有待定照片已审阅完毕</p>
    </div>

    <div class="pending-actions-bottom">
      <button class="confirm-btn" @click="confirmAll">
        {{ pendingPhotos.length > 0 ? '放弃剩余全部' : '确认并导出' }} →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const allPhotos = ref([])
const currentIndex = ref(0)

const pendingPhotos = computed(() => allPhotos.value.filter(p => p.is_pending))
const currentPhoto = computed(() => pendingPhotos.value[currentIndex.value] || {})
const selectedCount = computed(() => allPhotos.value.filter(p => p.is_selected).length)
const rejectedCount = computed(() => allPhotos.value.filter(p => p.is_rejected).length)

async function decide(id, action) {
  try {
    if (action === 'select') {
      await axios.post(`/api/pending/${id}/select`)
    } else {
      await axios.post(`/api/pending/${id}/reject`)
    }
    await loadPhotos()
    if (currentIndex.value >= pendingPhotos.value.length && currentIndex.value > 0) {
      currentIndex.value = pendingPhotos.value.length - 1
    }
  } catch (e) {
    alert('操作失败: ' + e.message)
  }
}

async function confirmAll() {
  try {
    await axios.post('/api/pending/confirm')
    await loadPhotos()
    router.push('/confirm')
  } catch (e) {
    alert('确认失败: ' + e.message)
  }
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  allPhotos.value = res.data
}

onMounted(loadPhotos)
</script>

<style scoped>
.pending-view { padding: 1.5rem 2rem; max-width: 600px; margin: 0 auto; }
.pending-view h2 { margin-bottom: 0.5rem; text-align: center; }
.summary { color: #aaa; margin-bottom: 1rem; text-align: center; }
.pending-stats { display: flex; gap: 2rem; justify-content: center; margin-bottom: 1.5rem; color: #888; }
.pending-area { text-align: center; }
.pending-card { background: #16213e; border-radius: 12px; padding: 1.5rem; }
.pending-img { max-width: 100%; max-height: 55vh; object-fit: contain; border-radius: 8px; cursor: pointer; }
.pending-info { margin-top: 1rem; display: flex; gap: 1rem; justify-content: center; }
.pending-score { color: #4caf50; }
.pending-name { color: #888; }
.pending-actions { display: flex; gap: 2rem; justify-content: center; margin-top: 1rem; }
.select-btn { padding: 0.6rem 2rem; background: #4caf50; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.reject-btn { padding: 0.6rem 2rem; background: #c0392b; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.pending-nav { margin-top: 1rem; color: #666; }
.pending-actions-bottom { text-align: center; margin-top: 1.5rem; }
.confirm-btn { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
</style>
