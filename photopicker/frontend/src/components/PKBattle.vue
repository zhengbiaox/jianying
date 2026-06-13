<template>
  <div class="pk-battle">
    <div class="pk-top-actions">
      <a-space>
        <a-button type="outline" @click="$emit('choose', 'none')">暂缓</a-button>
        <a-button type="primary" @click="$emit('choose', 'both')">全部保留</a-button>
      </a-space>
    </div>
    
    <div class="pk-sides">
      <div class="pk-side">
        <img :src="'/api/preview/' + left.id" @click="$emit('zoom', left.id, right?.id)" />
        <div class="pk-info">
          <a-tag color="blue">{{ left.score }} 分</a-tag>
          <div class="pk-exif" v-if="leftExif">
            <a-tag v-if="leftExif.shutter" size="small">{{ leftExif.shutter }}</a-tag>
            <a-tag v-if="leftExif.aperture" size="small">{{ leftExif.aperture }}</a-tag>
            <a-tag v-if="leftExif.iso" size="small">{{ leftExif.iso }}</a-tag>
          </div>
          <a-button type="primary" status="danger" @click="$emit('choose', 'left')">← 保留</a-button>
        </div>
      </div>
      
      <div class="pk-vs" v-if="right">VS</div>
      
      <div class="pk-side" v-if="right">
        <img :src="'/api/preview/' + right.id" @click="$emit('zoom', left.id, right.id)" />
        <div class="pk-info">
          <a-tag color="blue">{{ right.score }} 分</a-tag>
          <div class="pk-exif" v-if="rightExif">
            <a-tag v-if="rightExif.shutter" size="small">{{ rightExif.shutter }}</a-tag>
            <a-tag v-if="rightExif.aperture" size="small">{{ rightExif.aperture }}</a-tag>
            <a-tag v-if="rightExif.iso" size="small">{{ rightExif.iso }}</a-tag>
          </div>
          <a-button type="primary" status="info" @click="$emit('choose', 'right')">保留 →</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  left: { type: Object, required: true },
  right: { type: Object, default: null }
})
defineEmits(['choose', 'zoom'])

const leftExif = ref(null)
const rightExif = ref(null)

async function loadExif() {
  if (props.left?.id) {
    try { leftExif.value = (await axios.get(`/api/exif/${props.left.id}`)).data } catch {}
  }
  if (props.right?.id) {
    try { rightExif.value = (await axios.get(`/api/exif/${props.right.id}`)).data } catch {}
  }
}

watch(() => [props.left?.id, props.right?.id], loadExif, { immediate: true })
</script>

<style scoped>
.pk-battle { padding: 1rem; }
.pk-top-actions { text-align: center; margin-bottom: 1rem; }
.pk-sides { display: flex; align-items: center; gap: 1.5rem; }
.pk-side { flex: 1; text-align: center; }
.pk-side img { width: 100%; max-height: 65vh; object-fit: contain; border-radius: 8px; cursor: pointer; }
.pk-info { margin-top: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.pk-exif { display: flex; gap: 0.5rem; }
.pk-vs { font-size: 2rem; color: #555; font-weight: bold; }
</style>
