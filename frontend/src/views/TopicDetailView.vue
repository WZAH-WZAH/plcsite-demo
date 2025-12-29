<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()

const posts = ref([])
const loading = ref(true)
const sortType = ref('new') // new | hot
const topicName = ref('')

async function fetchPosts() {
  loading.value = true
  topicName.value = String(route.params.name || '').trim()

  try {
    const params = {
      'tags__name': topicName.value,
      sort: sortType.value === 'hot' ? 'hot' : 'created',
      range: 'week',
    }
    const { data } = await apiGet('/api/posts/', { params, __skipAuth: true })
    posts.value = unwrapList(data)
  } finally {
    loading.value = false
  }
}

watch(() => route.params.name, fetchPosts)
watch(sortType, fetchPosts)
onMounted(fetchPosts)
</script>

<template>
  <div class="topic-page">
    <div class="topic-header">
      <div class="topic-title"><span class="hash">#</span>{{ topicName }}</div>

      <div class="topic-tabs">
        <button :class="{ active: sortType === 'new' }" @click="sortType = 'new'">最新发布</button>
        <button :class="{ active: sortType === 'hot' }" @click="sortType = 'hot'">热门讨论</button>
      </div>
    </div>

    <div class="topic-content">
      <div v-if="loading" class="muted">加载中...</div>
      <div v-else-if="posts.length" class="bili-grid">
        <PostPreviewCard v-for="p in posts" :key="p.id" :post="p" />
      </div>
      <div v-else class="empty-state">暂无相关内容，快去发布第一条带有 #{{ topicName }} 的帖子吧！</div>
    </div>
  </div>
</template>

<style scoped>
.topic-page {
  max-width: 1000px;
  margin: 0 auto;
  min-height: 100vh;
  background: #fff;
}

.topic-header {
  padding: 40px 20px 20px;
  border-bottom: 1px solid #e3e5e7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.topic-title {
  font-size: 28px;
  font-weight: 800;
  color: #18191c;
}

.hash {
  color: #00aeec;
  margin-right: 4px;
}

.topic-tabs {
  display: flex;
  gap: 20px;
}

.topic-tabs button {
  background: none;
  border: none;
  font-size: 16px;
  color: #61666d;
  cursor: pointer;
  padding-bottom: 6px;
  border-bottom: 3px solid transparent;
}

.topic-tabs button.active {
  color: #00aeec;
  border-bottom-color: #00aeec;
  font-weight: 600;
}

.topic-content {
  padding: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #999;
}

.bili-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

@media (max-width: 980px) {
  .bili-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .topic-header {
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
  }

  .bili-grid {
    grid-template-columns: 1fr;
  }
}
</style>
