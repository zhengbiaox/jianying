<template>
  <div class="rejected-pool">
    <h3>待定区 ({{ photos.length }})</h3>
    <div class="pool-grid">
      <div
        v-for="photo in photos"
        :key="photo.id"
        class="pool-thumb"
        :style="{ borderColor: gradeColor(photo.grade) }"
      >
        <img :src="'/api/thumbnail/' + photo.id" loading="lazy" />
        <div class="pool-overlay">
          <span class="score">{{ photo.score }}</span>
          <button class="rescue-btn" @click="$emit('rescue', photo.id)">捞回</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  photos: { type: Array, default: () => [] }
})
defineEmits(['rescue'])

function gradeColor(grade) {
  return { green: '#4caf50', yellow: '#ff9800', red: '#f44336' }[grade] || '#666'
}
</script>

<style scoped>
.rejected-pool { background: #111; border-top: 1px solid #333; padding: 1rem 2rem; }
.rejected-pool h3 { margin-bottom: 0.8rem; color: #aaa; }
.pool-grid { display: flex; gap: 0.5rem; overflow-x: auto; padding-bottom: 0.5rem; }
.pool-thumb { position: relative; width: 100px; height: 100px; flex-shrink: 0; border: 2px solid; border-radius: 6px; overflow: hidden; cursor: pointer; }
.pool-thumb img { width: 100%; height: 100%; object-fit: cover; }
.pool-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); display: flex; justify-content: space-between; align-items: center; padding: 2px 6px; }
.score { font-size: 0.75rem; color: #fff; }
.rescue-btn { font-size: 0.65rem; padding: 2px 6px; background: #0f3460; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.rescue-btn:hover { background: #1a5276; }
</style>
