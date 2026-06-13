<template>
  <div class="confirm-view">
    <a-typography-title :heading="4">确认 · 导出</a-typography-title>
    
    <a-result v-if="!pkComplete" status="warning" title="尚有未完成的甄选">
      <template #subtitle>
        <p>已完成 {{ pkStatus.finished_groups }} / {{ pkStatus.total_groups }} 个场景</p>
        <p>已保留 {{ pkStatus.selected_count }} 张</p>
      </template>
      <template #extra>
        <a-button type="primary" @click="$router.push('/pick')">继续甄选 →</a-button>
      </template>
    </a-result>
    
    <div v-else>
      <a-space style="margin-bottom: 1rem;">
        <a-tag color="green">入选 {{ selectedPhotos.length }} 张</a-tag>
        <a-tag color="red">淘汰 {{ rejectedCount }} 张</a-tag>
      </a-space>
      
      <a-grid :cols="5" :col-gap="8" :row-gap="8" style="max-height: 40vh; overflow-y: auto; margin-bottom: 1.5rem;">
        <a-grid-item v-for="photo in selectedPhotos" :key="photo.id">
          <a-card :bordered="true" hoverable>
            <template #cover>
              <img :src="'/api/thumbnail/' + photo.id" style="width: 100%; height: 80px; object-fit: cover;" />
            </template>
            <a-tag color="green" size="small">{{ photo.score }} 分</a-tag>
          </a-card>
        </a-grid-item>
      </a-grid>
      
      <a-space direction="vertical" style="width: 100%;">
        <a-radio-group v-model="mode" type="button">
          <a-radio value="copy">复制 · 保留原件</a-radio>
          <a-radio value="move">移动 · 节省空间</a-radio>
        </a-radio-group>
        <a-button type="primary" size="large" long :loading="exporting" @click="doExport">导出并归档</a-button>
      </a-space>
      
      <a-result v-if="exportResult" status="success" title="归档完成" style="margin-top: 1rem;">
        <template #subtitle>
          <p>入选 {{ exportResult['入选'] }} 张 · 淘汰 {{ exportResult['未入选'] }} 张</p>
        </template>
      </a-result>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const allPhotos = ref([])
const pkStatus = ref({ complete: false, total_groups: 0, finished_groups: 0, selected_count: 0 })
const mode = ref('copy')
const exporting = ref(false)
const exportResult = ref(null)

const pkComplete = computed(() => pkStatus.value.complete)
const selectedPhotos = computed(() => allPhotos.value.filter(p => p.is_selected))
const rejectedCount = computed(() => allPhotos.value.filter(p => p.is_rejected).length)

async function loadStatus() { try { pkStatus.value = (await axios.get('/api/pk/status')).data } catch {} }
async function loadPhotos() { allPhotos.value = (await axios.get('/api/photos')).data }

async function doExport() {
  exporting.value = true
  try {
    exportResult.value = (await axios.post('/api/export/final', null, { params: { mode: mode.value } })).data
  } catch (e) { console.error(e) }
  finally { exporting.value = false }
}

onMounted(() => { loadStatus(); loadPhotos() })
</script>

<style scoped>
.confirm-view { padding: 1.5rem 2rem; }
</style>
