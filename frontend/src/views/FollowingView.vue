<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, unwrapList } from '../api'
import TimelineItem from '../components/TimelineItem.vue'

const posts = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet('/api/posts/feed/following/', {})
    posts.value = unwrapList(data)
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败，请稍后再试。'
    posts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="layout-grid">
      <div class="timeline-wrapper">
        <div class="timeline-header">
          <h2>关注动态</h2>
        </div>
        <div v-if="loading" style="padding: 20px; text-align: center">加载中...</div>
        <div v-else-if="error" style="padding: 20px; text-align: center; color: #ef4444">{{ error }}</div>
        <div v-else>
          <TimelineItem v-for="p in posts" :key="p.id" :post="p" />
        </div>
      </div>

      <div class="right-sidebar">
        <div class="sidebar-card muted">关注作者或板块后，这里会显示你的关注动态。</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  min-height: 100vh;
}
.layout-grid {
  display: flex;
  width: 100%;
  max-width: 1000px;
  align-items: flex-start;
}
.timeline-wrapper {
  width: 600px;
  background: #fff;
  border-left: 1px solid #eff3f4;
  border-right: 1px solid #eff3f4;
  min-height: 100vh;
}
.timeline-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
}
.right-sidebar {
  width: 340px;
  padding: 14px;
}
.sidebar-card {
  background: #fff;
  border: 1px solid #eff3f4;
  border-radius: 10px;
  padding: 14px;
}
</style>
