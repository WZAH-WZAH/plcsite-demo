<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiGet, unwrapList } from '../api'
import { auth } from '../auth'
import { ui } from '../ui'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()
const router = useRouter()
const user = ref(null)
const posts = ref([])
const loading = ref(true)
const error = ref('')

const followLoading = ref(false)

const bannerInput = ref(null)
const bannerUploading = ref(false)

// 判断是否是本人
const isMe = computed(() => {
  const mePid = String(auth.state.me?.pid || '').trim()
  const pagePid = String(user.value?.pid || '').trim()
  return Boolean(mePid && pagePid && mePid === pagePid)
})

async function loadData() {
  loading.value = true
  error.value = ''
  user.value = null
  posts.value = []

  const pid = String(route.params.pid || '').trim()
  try {
    if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
      await auth.loadMe()
    }

    if (!pid) {
      error.value = '缺少用户 PID。'
      return
    }
    const { data: u } = await apiGet(`/api/users/${pid}/`, auth.isAuthed() ? {} : { __skipAuth: true })
    user.value = u

    const { data } = await apiGet('/api/posts/', { params: { author__pid: pid }, __skipAuth: true })
    posts.value = unwrapList(data)
  } catch (e) {
    console.error(e)
    const status = e?.response?.status
    if (status === 404) error.value = '用户不存在。'
    else error.value = '加载失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}

async function toggleFollow() {
  if (!user.value) return
  if (!auth.isAuthed()) {
    router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  if (followLoading.value) return

  followLoading.value = true
  try {
    const pid = String(user.value?.pid || '').trim()
    const wasFollowing = Boolean(user.value?.is_following)
    const { data } = await api.post(`/api/users/${pid}/follow/`)
    user.value.is_following = Boolean(data?.following)
    if (typeof data?.followers_count === 'number') user.value.followers_count = data.followers_count
    if (wasFollowing && !user.value.is_following) {
      ui.openModal('已取消关注', { title: '提示' })
    }
  } catch (e) {
    ui.openModal(e?.response?.data?.detail || '操作失败，请稍后再试。', { title: '提示' })
  } finally {
    followLoading.value = false
  }
}

function goToSettings() {
  router.push('/me')
}

function triggerBannerUpload() {
  if (!isMe.value) return
  bannerInput.value?.click?.()
}

async function onBannerChange(e) {
  const file = e?.target?.files?.[0]
  if (!file) return
  bannerUploading.value = true
  try {
    const fd = new FormData()
    fd.append('banner', file)
    const { data } = await api.patch('/api/users/me/', fd)
    // 只更新当前页面的 banner_url
    if (user.value) user.value.banner_url = data?.banner_url || user.value.banner_url
    await auth.loadMe()
    alert('头图更新成功')
  } catch (e2) {
    alert(e2?.response?.data?.detail || '头图上传失败')
  } finally {
    bannerUploading.value = false
    if (e?.target) e.target.value = ''
  }
}

onMounted(loadData)
watch(() => route.params.pid, loadData)
</script>

<template>
  <div v-if="user" class="space-container">
    <div
      class="space-banner"
      :style="{ backgroundImage: user.banner_url ? `url(${user.banner_url})` : '' }"
    >
      <div class="banner-gradient"></div>

      <button
        v-if="isMe"
        class="edit-banner-btn"
        type="button"
        :disabled="bannerUploading"
        @click.stop="triggerBannerUpload"
      >
        📷 {{ bannerUploading ? '上传中...' : '更换头图' }}
      </button>

      <input
        v-if="isMe"
        ref="bannerInput"
        type="file"
        hidden
        accept="image/*"
        @change="onBannerChange"
      />

      <div class="user-info-wrapper">
        <div class="avatar-holder">
          <img v-if="user.avatar_url" :src="user.avatar_url" class="big-avatar" />
          <div v-else class="big-avatar placeholder"></div>
        </div>
        <div class="text-info">
          <div class="name-row">
            <span class="name">{{ user.nickname || user.username || user.pid }}</span>
            <span class="level-tag">Lv6</span>
          </div>
          <div class="bio">{{ user.bio }}</div>
        </div>

        <div class="action-area">
          <button v-if="isMe" class="btn-edit" type="button" @click="goToSettings">编辑资料</button>
          <button
            v-else
            class="btn-follow"
            :class="{ following: !!user.is_following }"
            type="button"
            :disabled="followLoading"
            @click="toggleFollow"
          >
            {{ user.is_following ? '已关注' : '+ 关注' }}
          </button>
        </div>
      </div>
    </div>

    <div class="space-nav">
      <div class="nav-inner">
        <div class="nav-item"><span>🏠</span> 主页</div>
        <div class="nav-item active"><span>▶️</span> 投稿 <span class="nav-num">{{ posts.length }}</span></div>
        <div class="nav-item"><span>⭐</span> 收藏 <span class="nav-num">0</span></div>
        <div class="nav-right">
          <div class="stat-box">
            <div class="stat-label">关注数</div>
            <div class="stat-val">{{ user.following_count ?? 0 }}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">粉丝数</div>
            <div class="stat-val">{{ user.followers_count ?? 0 }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="space-content">
      <h3 class="section-title">我的投稿</h3>
      <div class="bili-grid">
        <PostPreviewCard v-for="p in posts" :key="p.id" :post="p" />
      </div>
      <div v-if="posts.length === 0" class="empty-state">空空如也</div>
    </div>
  </div>

  <div v-else-if="loading" class="loading-screen">加载中...</div>

  <div v-else class="loading-screen">
    <div class="error-box">
      <div class="error-title">{{ error || '加载失败' }}</div>
      <div class="error-tip">请检查链接是否正确（PID），或稍后重试。</div>
    </div>
  </div>
</template>

<style scoped>
.space-container {
  background: #fff;
  min-height: 100vh;
}

.loading-screen {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.error-box {
  text-align: center;
}

.error-title {
  font-size: 16px;
  color: #111827;
  font-weight: 600;
}

.error-tip {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

/* Banner */
.space-banner {
  height: 240px;
  background-size: cover;
  background-position: center;
  background-color: #f1f2f3;
  position: relative;
  display: flex;
  align-items: flex-end;
}
.banner-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.5), transparent);
}
.user-info-wrapper {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-end;
  padding: 0 20px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  transform: translateY(20px);
}
.avatar-holder {
  width: 100px;
  height: 100px;
  border: 4px solid rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  overflow: hidden;
  background: #fff;
  margin-right: 20px;
}
.big-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.big-avatar.placeholder {
  width: 100%;
  height: 100%;
  background: #f1f2f3;
}
.text-info {
  margin-bottom: 30px;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  flex: 1;
}
.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.name {
  font-size: 22px;
  font-weight: 700;
}
.level-tag {
  background: #f04c49;
  font-size: 10px;
  padding: 0 4px;
  border-radius: 2px;
}
.bio {
  font-size: 13px;
  opacity: 0.9;
}

.edit-banner-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.space-banner:hover .edit-banner-btn {
  opacity: 1;
}

.edit-banner-btn:disabled {
  opacity: 1;
  cursor: not-allowed;
}

.action-area {
  margin-bottom: 30px;
}

.btn-edit,
.btn-follow {
  padding: 6px 24px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-follow.following {
  background: #f3f4f6;
  color: #6b7280;
  border-color: #e5e7eb;
}

.btn-edit {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(4px);
}

.btn-edit:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-follow {
  background: #00aeec;
  color: #fff;
}

.btn-follow:disabled {
  opacity: 0.8;
  cursor: not-allowed;
}

/* Nav Bar */
.space-nav {
  height: 66px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  padding-left: 140px;
}
.nav-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 100%;
}
.nav-item {
  margin-right: 30px;
  font-size: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #18191c;
}
.nav-item.active {
  color: #00aeec;
  border-bottom: 3px solid #00aeec;
  height: 100%;
  margin-bottom: -3px;
}
.nav-num {
  font-size: 12px;
  color: #9499a0;
  background: #f1f2f3;
  padding: 0 4px;
  border-radius: 4px;
}
.nav-right {
  margin-left: auto;
  display: flex;
  gap: 20px;
}
.stat-box {
  text-align: center;
}
.stat-label {
  font-size: 12px;
  color: #9499a0;
}
.stat-val {
  font-size: 16px;
  color: #18191c;
  font-weight: 600;
}

/* Content */
.space-content {
  max-width: 1100px;
  margin: 30px auto;
  padding: 0 20px;
}
.section-title {
  font-size: 20px;
  margin-bottom: 20px;
  font-weight: 400;
  color: #000;
}
.empty-state {
  padding: 50px;
  text-align: center;
  color: #999;
}
.loading-screen {
  text-align: center;
  padding: 50px;
  color: #999;
}
</style>
