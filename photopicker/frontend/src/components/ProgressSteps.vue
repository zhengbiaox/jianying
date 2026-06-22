<template>
  <div class="progress-steps">
    <div v-for="(step, idx) in steps" :key="idx"
         class="step" :class="{ active: idx === current, done: idx < current }">
      <span class="step-icon">{{ idx < current ? '✓' : idx === current ? '→' : '○' }}</span>
      <span class="step-label">{{ step }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => ['导入', '技术筛选', '最佳选择', '导出'] },
  current: { type: Number, default: 0 }
})
</script>

<style scoped>
.progress-steps { display: flex; justify-content: center; gap: 1rem; padding: 1rem 2rem; background: #16213e; border-bottom: 1px solid #333; }
.step { display: flex; align-items: center; gap: 0.4rem; color: #666; font-size: 0.9rem; }
.step.active { color: #4cc9f0; }
.step.done { color: #4caf50; }
.step-icon { font-size: 0.85rem; }
</style>
