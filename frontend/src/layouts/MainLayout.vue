<script setup>
import { RouterView } from 'vue-router'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="app">
    <TopBar />

    <main class="main">
      <div class="container">
        <RouterView />
      </div>
    </main>

    <footer class="footer">
      <div class="container muted">后端 API：/api · 开发环境</div>
    </footer>
  </div>
</template>
