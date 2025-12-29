<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import TimelineItem from '../components/TimelineItem.vue'

const router = useRouter()

const posts = ref([])
const loading = ref(true)

const sidebarLoading = ref(true)
const sidebarError = ref('')

// 后端数据
const hotTopics = ref([])
const recUsers = ref([])

const searchQuery = ref('')

function goSearch() {
  const q = String(searchQuery.value || '').trim()
  if (!q) return
  router.push({ path: '/search', query: { q } })
}

onMounted(async () => {
  try {
    const { data } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true })
    posts.value = unwrapList(data)
  } finally {
    loading.value = false
  }

  // Sidebar 数据单独加载，避免影响主时间线
  sidebarLoading.value = true
  sidebarError.value = ''
  try {
    const [trendingResp, recommendedResp] = await Promise.all([
      apiGet('/api/tags/trending/', { __skipAuth: true }),
      apiGet('/api/users/recommended/', { __skipAuth: true }),
    ])

    hotTopics.value = Array.isArray(trendingResp?.data) ? trendingResp.data : []
    recUsers.value = Array.isArray(recommendedResp?.data) ? recommendedResp.data : []
  } catch (e) {
    sidebarError.value = e?.response?.data?.detail || '侧边栏加载失败'
    hotTopics.value = []
    recUsers.value = []
  } finally {
    sidebarLoading.value = false
  }
})
</script>

<template>
  <div class="page-container">
    <div class="layout-grid">
      <div class="timeline-wrapper">
        <div class="timeline-header">
          <h2>最新动态</h2>
        </div>
        <div v-if="loading" style="padding: 20px; text-align: center">加载中...</div>
        <div v-else>
          <TimelineItem v-for="p in posts" :key="p.id" :post="p" />
        </div>
      </div>

      <div class="right-sidebar">
        <div class="search-box">
          <input
            v-model="searchQuery"
            placeholder="搜索动态..."
            class="sidebar-input"
            @keydown.enter="goSearch"
          />
        </div>

        <div class="sidebar-card">
          <h3>热门话题</h3>
          <div v-if="sidebarLoading" class="muted">加载中...</div>
          <div v-else-if="sidebarError" class="muted">{{ sidebarError }}</div>
          <div v-else>
            <div class="topic-item" v-for="t in hotTopics" :key="t.id" @click="router.push(`/topic/${t.name}`)">
              <span class="topic-name">#{{ t.name }}#</span>
              <span class="topic-count">{{ (t.posts_7d ?? t.usage_count ?? 0) }}</span>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <h3>推荐关注</h3>
          <div v-if="sidebarLoading" class="muted">加载中...</div>
          <div v-else-if="sidebarError" class="muted">{{ sidebarError }}</div>
          <div v-else>
            <div class="user-item" v-for="u in recUsers" :key="u.pid">
              <img v-if="u.avatar_url" class="u-avatar" :src="u.avatar_url" alt="avatar" />
              <div v-else class="u-avatar placeholder"></div>
              <div class="u-info">
                <div class="u-name">{{ u.nickname || u.username || u.pid }}</div>
                <div class="u-desc">粉丝 {{ u.followers_count ?? 0 }}</div>
              </div>
              <button class="btn-follow" type="button" disabled>+关注</button>
            </div>
          </div>
        </div>

        <div class="footer-links">© 2024 PLC Community</div>
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

/* Timeline */
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
  padding: 0 16px;
  height: 53px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #eff3f4;
}
.timeline-header h2 {
  font-size: 19px;
  font-weight: 700;
  margin: 0;
}

/* Sidebar */
.right-sidebar {
  width: 350px;
  padding: 12px 24px;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sidebar-input {
  width: 100%;
  padding: 10px 20px;
  border-radius: 99px;
  border: 1px solid #eff3f4;
  background: #eff3f4;
  outline: none;
}
.sidebar-input:focus {
  background: #fff;
  border-color: #1d9bf0;
}

.sidebar-card {
  background: #f7f9f9;
  border-radius: 16px;
  padding: 16px;
}
.sidebar-card h3 {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 12px;
}

.topic-item {
  padding: 8px 0;
  cursor: pointer;
  color: #0f1419;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.topic-item:hover {
  color: #1d9bf0;
}

.topic-count {
  font-size: 12px;
  color: #536471;
  font-weight: 500;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.u-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  background: #ccc;
}
.u-avatar.placeholder {
  background: #ccc;
}
.u-info {
  flex: 1;
}
.u-name {
  font-weight: 700;
  font-size: 14px;
}
.u-desc {
  color: #536471;
  font-size: 12px;
}
.btn-follow {
  background: #000;
  color: #fff;
  border: none;
  border-radius: 99px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.muted {
  color: #536471;
  font-size: 13px;
  padding: 6px 0;
}

.footer-links {
  font-size: 12px;
  color: #536471;
  padding: 0 16px;
}

@media (max-width: 980px) {
  .right-sidebar {
    display: none;
  }
  .timeline-wrapper {
    border-right: none;
  }
}
</style>