<template>
  <div class="import-view">
    <div class="import-area" @click="selectFolder">
      <div class="import-icon">📁</div>
      <p>点击选择照片文件夹</p>
      <p class="hint">支持 JPG + RAW，自动配对</p>
    </div>

    <div v-if="importing" class="progress">
      <p>正在扫描... 已发现 {{ count }} 张照片</p>
    </div>

    <div v-if="done" class="done">
      <p>✅ 导入完成，共 {{ count }} 张照片</p>
      <button @click="$router.push('/filter')">开始初筛 →</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const importing = ref(false)
const done = ref(false)
const count = ref(0)

async function selectFolder() {
  const path = prompt('请输入照片文件夹路径:')
  if (!path) return

  importing.value = true
  done.value = false

  try {
    const res = await axios.post('/api/import', null, {
      params: { folder_path: path }
    })
    count.value = res.data.count
    done.value = true
  } catch (e) {
    alert('导入失败: ' + e.message)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-view { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; }
.import-area { width: 400px; height: 300px; border: 2px dashed #555; border-radius: 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
.import-area:hover { border-color: #0f3460; background: rgba(15,52,96,0.2); }
.import-icon { font-size: 3rem; margin-bottom: 1rem; }
.hint { color: #888; font-size: 0.85rem; margin-top: 0.5rem; }
.done { margin-top: 2rem; text-align: center; }
.done button { margin-top: 1rem; padding: 0.8rem 2rem; background: #0f3460; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; }
.done button:hover { background: #1a5276; }
</style>
