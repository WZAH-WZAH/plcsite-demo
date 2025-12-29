<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, apiGet, unwrapList } from '../api'
import TimelineItem from '../components/TimelineItem.vue'
import { ui } from '../ui'
import { auth } from '../auth'

const posts = ref([])
const loading = ref(true)
const error = ref('')

const searchQuery = ref('')

// Sidebar recommended users
const sidebarLoading = ref(true)
const sidebarError = ref('')
const recUsers = ref([])
const followBusyPid = ref('')

const followedUserPosts = computed(() => {
  return (posts.value || []).filter((p) => !!p?.is_following_author)
})

const visiblePosts = computed(() => {
  const q = String(searchQuery.value || '').trim().toLowerCase()
  if (!q) return posts.value || []
  // Search results are restricted to followed users' posts only.
  const src = followedUserPosts.value
  return src.filter((p) => {
    const title = String(p?.title || '').toLowerCase()
    const body = String(p?.body || '').toLowerCase()
    const author = String(p?.author_nickname || p?.author_username || '').toLowerCase()
    const tags = Array.isArray(p?.tags_details) ? p.tags_details.map((t) => String(t?.name || '')).join(' ').toLowerCase() : ''
    return title.includes(q) || body.includes(q) || author.includes(q) || tags.includes(q)
  })
})

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

async function loadSidebar() {
  sidebarLoading.value = true
  sidebarError.value = ''
  try {
    const { data } = await apiGet('/api/users/recommended/', {})
    recUsers.value = Array.isArray(data) ? data : unwrapList(data)
  } catch (e) {
    sidebarError.value = e?.response?.data?.detail || '侧边栏加载失败'
    recUsers.value = []
  } finally {
    sidebarLoading.value = false
  }
}

async function toggleFollow(u) {
  const pid = String(u?.pid || '').trim()
  if (!pid) return
  if (!auth.isAuthed()) return
  if (followBusyPid.value) return

  followBusyPid.value = pid
  try {
    const wasFollowing = Boolean(u?.is_following)
    const { data } = await api.post(`/api/users/${pid}/follow/`)
    const following = Boolean(data?.following)
    u.is_following = following
    if (typeof data?.followers_count === 'number') u.followers_count = data.followers_count
    if (wasFollowing && !following) ui.openModal('已取消关注', { title: '提示' })
  } catch (e) {
    ui.openModal(e?.response?.data?.detail || '操作失败，请稍后再试。', { title: '提示' })
  } finally {
    followBusyPid.value = ''
  }
}

onMounted(async () => {
  if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
    await auth.loadMe()
  }
  await Promise.all([load(), loadSidebar()])
})
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
          <div v-if="searchQuery" class="muted" style="padding: 10px 16px">
            搜索结果（仅关注用户发帖）：{{ visiblePosts.length }}
            <button type="button" class="btn" style="margin-left: 10px" @click="searchQuery = ''">清除</button>
          </div>
          <TimelineItem v-for="p in visiblePosts" :key="p.id" :post="p" />
        </div>
      </div>

      <div class="right-sidebar">
        <div class="search-box">
          <input
            v-model="searchQuery"
            placeholder="在关注的人里搜索..."
            class="sidebar-input"
            @keydown.enter.prevent
          />
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
              <button
                class="btn-follow"
                :class="{ following: !!u.is_following }"
                type="button"
                :disabled="followBusyPid === String(u.pid || '')"
                @click="toggleFollow(u)"
              >
                {{ u.is_following ? '已关注' : '+关注' }}
              </button>
            </div>
          </div>
        </div>
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
.right-sidebar {
  width: 350px;
  padding: 12px 24px;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.search-box {
  display: block;
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

.btn-follow.following {
  background: #f3f4f6;
  color: #6b7280;
}

.muted {
  color: #536471;
  font-size: 13px;
  padding: 6px 0;
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
