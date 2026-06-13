<template>
  <div class="pending-view">
    <a-typography-title :heading="4">权衡 · 待定审阅</a-typography-title>
    <a-typography-text type="secondary">以下照片暂缓决定，请逐张审阅</a-typography-text>
    
    <a-space style="margin: 1rem 0;">
      <a-tag color="orange">待审 {{ pendingPhotos.length }} 张</a-tag>
      <a-tag color="green">已保留 {{ selectedCount }} 张</a-tag>
      <a-tag color="red">已放弃 {{ rejectedCount }} 张</a-tag>
    </a-space>
    
    <a-card v-if="pendingPhotos.length > 0" style="background: #16213e;">
      <img :src="'/api/preview/' + currentPhoto.id" style="width: 100%; max-height: 55vh; object-fit: contain; border-radius: 8px; cursor: pointer;" />
      <div style="margin-top: 1rem; text-align: center;">
        <a-space>
          <a-tag color="blue">{{ currentPhoto.score }} 分</a-tag>
          <a-tag>{{ currentPhoto.path?.split('/').pop() }}</a-tag>
        </a-space>
      </div>
      <a-space style="margin-top: 1rem; display: flex; justify-content: center;">
        <a-button type="primary" status="success" size="large" @click="decide(currentPhoto.id, 'select')">保留</a-button>
        <a-button type="primary" status="danger" size="large" @click="decide(currentPhoto.id, 'reject')">放弃</a-button>
      </a-space>
      <div style="text-align: center; margin-top: 0.5rem;">
        <a-tag>{{ currentIndex + 1 }} / {{ pendingPhotos.length }}</a-tag>
      </div>
    </a-card>
    
    <a-result v-else status="success" title="所有待定照片已审阅完毕">
      <template #extra>
        <a-button type="primary" @click="confirmAll">确认并导出 →</a-button>
      </template>
    </a-result>
    
    <div style="text-align: center; margin-top: 1.5rem;">
      <a-button type="primary" @click="confirmAll">
        {{ pendingPhotos.length > 0 ? '放弃剩余全部' : '确认并导出' }} →
      </a-button>
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
    if (action === 'select') await axios.post(`/api/pending/${id}/select`)
    else await axios.post(`/api/pending/${id}/reject`)
    await loadPhotos()
    if (currentIndex.value >= pendingPhotos.value.length && currentIndex.value > 0) currentIndex.value--
  } catch {}
}

async function confirmAll() {
  try {
    await axios.post('/api/pending/confirm')
    await loadPhotos()
    router.push('/confirm')
  } catch {}
}

async function loadPhotos() { allPhotos.value = (await axios.get('/api/photos')).data }
onMounted(loadPhotos)
</script>

<style scoped>
.pending-view { padding: 1.5rem 2rem; max-width: 600px; margin: 0 auto; }
</style>
