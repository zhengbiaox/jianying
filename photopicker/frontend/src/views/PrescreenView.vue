<template>
  <div class="prescreen-view">
    <a-typography-title :heading="4">筛选 · 建议淘汰</a-typography-title>
    <a-typography-text type="secondary">以下照片质量欠佳，可挽回保留</a-typography-text>
    
    <a-space style="margin: 1rem 0;">
      <a-tag color="red">建议淘汰 {{ rejectedPhotos.length }} 张</a-tag>
      <a-tag color="green">已挽回 {{ rescuedCount }} 张</a-tag>
    </a-space>
    
    <a-grid :cols="5" :col-gap="12" :row-gap="12">
      <a-grid-item v-for="photo in rejectedPhotos" :key="photo.id">
        <a-card :bordered="true" hoverable @click="openPreview(photo.id)">
          <template #cover>
            <img :src="'/api/thumbnail/' + photo.id" style="width: 100%; height: 100px; object-fit: cover;" />
          </template>
          <a-space direction="vertical" size="mini">
            <a-tag color="red" size="small">{{ photo.score }} 分</a-tag>
            <a-space wrap size="mini">
              <a-tag v-for="r in getReasons(photo)" :key="r" color="orange" size="small">{{ r }}</a-tag>
            </a-space>
            <a-button v-if="!rescuedIds.has(photo.id)" type="primary" size="mini" status="success" @click.stop="rescue(photo.id)">挽回</a-button>
            <a-button v-else type="outline" size="mini" @click.stop="undoRescue(photo.id)">撤销挽回</a-button>
          </a-space>
        </a-card>
      </a-grid-item>
    </a-grid>
    
    <div style="text-align: center; margin-top: 1.5rem;">
      <a-button type="primary" size="large" @click="confirm">确认并开始甄选 →</a-button>
    </div>
    
    <a-modal v-model:visible="previewVisible" :footer="false" :width="800">
      <img :src="'/api/preview/' + previewId" style="width: 100%;" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const photos = ref([])
const rescuedIds = ref(new Set())
const previewVisible = ref(false)
const previewId = ref('')

const rejectedPhotos = computed(() => photos.value.filter(p => p.score < 60))
const rescuedCount = computed(() => rescuedIds.value.size)

function getReasons(photo) {
  return photo.reasons && photo.reasons.length ? photo.reasons : ['画质有待提升']
}

function openPreview(id) {
  previewId.value = id
  previewVisible.value = true
}

async function rescue(id) {
  try {
    await axios.post(`/api/photos/${id}/rescue`)
    rescuedIds.value.add(id)
  } catch {}
}

async function undoRescue(id) {
  rescuedIds.value.delete(id)
}

async function confirm() {
  try {
    await axios.post('/api/prescreen/confirm')
    router.push('/pick')
  } catch {}
}

async function loadPhotos() {
  const res = await axios.get('/api/photos')
  photos.value = res.data
}

onMounted(loadPhotos)
</script>

<style scoped>
.prescreen-view { padding: 1.5rem 2rem; }
</style>
