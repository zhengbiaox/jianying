<template>
  <div class="grade-selector">
    <button
      v-for="g in grades"
      :key="g.level"
      :class="['grade-btn', { active: selected === g.level }]"
      @click="$emit('change', g.level)"
    >
      {{ g.icon }} {{ g.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  selected: { type: Number, default: 60 }
})
defineEmits(['change'])

const grades = [
  { level: 80, icon: '🟢', label: '严格' },
  { level: 60, icon: '🟡', label: '适中' },
  { level: 40, icon: '🔴', label: '宽松' },
]
</script>

<style scoped>
.grade-selector { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
.grade-btn { padding: 0.5rem 1.2rem; border: 1px solid #555; border-radius: 8px; background: transparent; color: #aaa; cursor: pointer; font-size: 0.95rem; transition: all 0.2s; }
.grade-btn.active { background: #0f3460; color: #fff; border-color: #0f3460; }
.grade-btn:hover { border-color: #0f3460; }
</style>
