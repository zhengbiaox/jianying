<template>
  <div class="pk-battle">
    <div class="pk-side" :class="{ winner: selectedSide === 'left' }">
      <img :src="'/api/thumbnail/' + left.id" @click="$emit('zoom', left.id, right.id)" />
      <div class="pk-info">
        <span class="pk-score">评分: {{ left.score }}</span>
        <button class="pk-btn left" @click="$emit('choose', 'left')">← 选这个</button>
      </div>
    </div>

    <div class="pk-vs">VS</div>

    <div class="pk-side" :class="{ winner: selectedSide === 'right' }">
      <img :src="'/api/thumbnail/' + right.id" @click="$emit('zoom', left.id, right.id)" />
      <div class="pk-info">
        <span class="pk-score">评分: {{ right.score }}</span>
        <button class="pk-btn right" @click="$emit('choose', 'right')">选这个 →</button>
      </div>
    </div>

    <div class="pk-actions">
      <button @click="$emit('choose', 'both')">两张都选</button>
      <button @click="$emit('choose', 'none')">都跳过</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  left: { type: Object, required: true },
  right: { type: Object, required: true }
})
defineEmits(['choose', 'zoom'])

const selectedSide = ref(null)
</script>

<style scoped>
.pk-battle { display: flex; align-items: center; gap: 1.5rem; padding: 1rem; }
.pk-side { flex: 1; text-align: center; border: 2px solid transparent; border-radius: 12px; padding: 0.5rem; transition: all 0.2s; }
.pk-side.winner { border-color: #4caf50; background: rgba(76,175,80,0.1); }
.pk-side img { width: 100%; max-height: 50vh; object-fit: contain; border-radius: 8px; cursor: pointer; }
.pk-info { margin-top: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.pk-score { color: #aaa; font-size: 0.95rem; }
.pk-btn { padding: 0.5rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.2s; }
.pk-btn.left { background: #e74c3c; color: #fff; }
.pk-btn.right { background: #3498db; color: #fff; }
.pk-btn:hover { opacity: 0.8; }
.pk-vs { font-size: 2rem; color: #555; font-weight: bold; }
.pk-actions { display: flex; gap: 1rem; justify-content: center; margin-top: 1rem; }
.pk-actions button { padding: 0.5rem 1.5rem; background: #333; color: #aaa; border: none; border-radius: 8px; cursor: pointer; }
.pk-actions button:hover { background: #444; color: #fff; }
</style>
