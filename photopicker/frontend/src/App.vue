<template>
  <div id="app">
    <nav class="top-nav">
      <router-link to="/import">导入</router-link>
      <router-link to="/filter">初筛</router-link>
      <router-link to="/pick">PK选片</router-link>
      <router-link to="/export">导出</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; }
.top-nav { display: flex; gap: 2rem; padding: 1rem 2rem; background: #16213e; border-bottom: 1px solid #333; }
.top-nav a { color: #aaa; text-decoration: none; font-size: 1.1rem; padding: 0.5rem 1rem; border-radius: 6px; transition: all 0.2s; }
.top-nav a.router-link-active { color: #fff; background: #0f3460; }
.top-nav a:hover { color: #fff; }
</style>
