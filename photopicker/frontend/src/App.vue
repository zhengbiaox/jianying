<template>
  <div id="app">
    <a-tabs :active-key="activeTab" @change="onTabChange" type="rounded" size="large">
      <a-tab-pane key="/import" title="开始"></a-tab-pane>
      <a-tab-pane key="/prescreen" title="筛选"></a-tab-pane>
      <a-tab-pane key="/pick" title="甄选"></a-tab-pane>
      <a-tab-pane key="/pending" title="权衡"></a-tab-pane>
      <a-tab-pane key="/confirm" title="确认"></a-tab-pane>
    </a-tabs>
    <router-view />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const activeTab = ref(route.path)

watch(() => route.path, (p) => { activeTab.value = p })

function onTabChange(key) {
  router.push(key)
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; }
#app .arco-tabs { padding: 0 2rem; background: #16213e; }
#app .arco-tabs-nav { border-bottom: 1px solid #333; }
</style>
