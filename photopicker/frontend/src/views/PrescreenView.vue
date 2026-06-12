<template>
  <div class="prescreen-view">
    <h2>废片审核</h2>
    <p class="summary">以下照片被检测为废片，你可以捞回或确认淘汰</p>

    <div class="prescreen-stats">
      <span>废片: {{ rejectedPhotos.length }} 张</span>
      <span>已捞回: {{ rescuedCount }} 张</span>
    </div>

    <div class="prescreen-grid">
      <div v-for="photo in rejectedPhotos" :key="photo.id"
           class="prescreen-card"
           :class="{ rescued: rescuedIds.has(photo.id) }">
        <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
        <div class="card-info">
          <span class="score">{{ photo.score }}</span>
          <div class="reasons">
            <span v-for="r in getReasons(photo)" :key="r" class="reason-tag">{{ r }}</span>
          </div>
        </div>
        <button v-if="!rescuedIds.has(photo.id)" class="rescue-btn" @click="rescue(photo.id)">
          捞回
        </button>
        <button v-else class="undo-btn" @click="undoRescue(photo.id)">
          取消捞回
        </button>
      </div>
    </div>

    <div class="prescreen-actions">
      <button class="confirm-btn" @click="confirm">
        确认淘汰，进入选片 →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const photos = ref([])
const rescuedIds = ref(new Set())

const rejectedPhotos = computed(() => photos.value.filter(p => p.score < 60))
const rescuedCount = computed(() => rescuedIds.value.size)

function getReasons(photo) {
  return photo.reasons && photo.reasons.length ? photo.reasons : ['质量不达标']
}

async function rescue(id) {
  try {
    await axios.post(`/api/photos/${id}/rescue`)
    rescuedIds.value.add(id)
  } catch (e) {
    alert('捞回失败: ' + e.message)
  }
}

async function undoRescue(id) {
  rescuedIds.value.delete(id)
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
.prescreen-card { background: #16213e; border-radius: 8px; overflow: hidden; border: 2px solid #c0392b; position: relative; }
.prescreen-card.rescued { border-color: #4caf50; opacity: 0.7; }
.prescreen-card img { width: 100%; height: 120px; object-fit: cover; }
.card-info { padding: 0.5rem; }
.score { background: #c0392b; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.reasons { margin-top: 0.3rem; display: flex; gap: 0.3rem; flex-wrap: wrap; }
.reason-tag { background: #333; color: #ff9800; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }
.rescue-btn, .undo-btn { position: absolute; bottom: 0.5rem; right: 0.5rem; padding: 0.3rem 0.8rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.rescue-btn { background: #4caf50; color: #fff; }
.undo-btn { background: #666; color: #aaa; }
.prescreen-actions { text-align: center; margin-top: 1.5rem; }
.confirm-btn { padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
</style>
