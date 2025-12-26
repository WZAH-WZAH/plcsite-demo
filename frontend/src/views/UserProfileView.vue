<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiGet, unwrapList } from '../api'
import { auth } from '../auth'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()
const router = useRouter()

const user = ref(null)
const posts = ref([])
const loading = ref(true)
const error = ref('')

const activeTab = ref('post') // 'home' | 'post' | 'fav'

// 头图上传
const bannerInput = ref(null)
const isUploadingBanner = ref(false)

const isMe = computed(() => {
  const mePid = String(auth.state.me?.pid || '').trim()
  const pagePid = String(user.value?.pid || '').trim()
  return Boolean(mePid && pagePid && mePid === pagePid)
})

const displayName = computed(() => {
  return user.value?.nickname || user.value?.username || user.value?.pid || ''
})

const avatarInitial = computed(() => {
  const base = String(displayName.value || '').trim()
  return base ? base.slice(0, 1).toUpperCase() : 'U'
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

    const { data: userData } = await apiGet(`/api/users/${pid}/`, { __skipAuth: true })
    user.value = userData

    const { data: postsData } = await apiGet('/api/posts/', {
      params: { author__pid: pid, ordering: '-created_at' },
      __skipAuth: true,
    })
    posts.value = unwrapList(postsData)
  } catch (e) {
    console.error('加载用户失败', e)
    const status = e?.response?.status
    if (status === 404) error.value = '用户不存在。'
    else error.value = '加载失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}

function goToSettings() {
  router.push('/me')
}

function triggerBannerUpload() {
  if (!isMe.value) return
  bannerInput.value?.click?.()
}

async function handleBannerChange(event) {
  const file = event?.target?.files?.[0]
  if (!file) return

  isUploadingBanner.value = true
  try {
    const fd = new FormData()
    fd.append('banner', file)
    const { data } = await api.patch('/api/users/me/', fd)

    if (user.value) {
      user.value.banner_url = data?.banner_url || user.value.banner_url
    }
    await auth.loadMe()
    alert('头图设置成功！')
  } catch (e) {
    console.error(e)
    alert(e?.response?.data?.detail || '头图上传失败，请重试')
  } finally {
    isUploadingBanner.value = false
    if (event?.target) event.target.value = ''
  }
}

function goNewPost() {
  router.push('/new')
}

onMounted(loadData)
watch(() => route.params.pid, loadData)
</script>

<template>
  <div v-if="user" class="bili-space">
    <div class="h-inner">
      <div class="h-banner" :style="{ backgroundImage: user.banner_url ? `url(${user.banner_url})` : '' }">
        <div class="h-gradient"></div>

        <div v-if="isMe" class="banner-edit-trigger" @click="triggerBannerUpload">
          <span v-if="isUploadingBanner">上传中...</span>
          <span v-else>📷 更换头图</span>
          <input
            type="file"
            ref="bannerInput"
            hidden
            accept="image/*"
            @change="handleBannerChange"
          />
        </div>
      </div>

      <div class="h-user-wrapper">
        <div class="h-avatar">
          <img v-if="user.avatar_url" :src="user.avatar_url" alt="avatar" />
          <div v-else class="avatar-fallback">{{ avatarInitial }}</div>
        </div>

        <div class="h-info">
          <div class="h-basic">
            <span class="h-name">{{ displayName }}</span>
            <span class="h-level">Lv6</span>
          </div>
          <div class="h-bio" :title="user.bio">{{ user.bio || '这个人很懒，什么都没有写' }}</div>
        </div>

        <div class="h-action">
          <template v-if="isMe">
            <button class="btn-primary-ghost" type="button" @click="goToSettings">编辑资料</button>
          </template>
          <template v-else>
            <button class="btn-primary" type="button">+ 关注</button>
            <button class="btn-ghost" type="button">发消息</button>
          </template>
        </div>
      </div>
    </div>

    <div class="n-inner">
      <div class="n-tab-list">
        <div class="n-tab" :class="{ active: activeTab === 'home' }" @click="activeTab = 'home'">
          <span class="n-icon">🏠</span> 主页
        </div>
        <div class="n-tab" :class="{ active: activeTab === 'post' }" @click="activeTab = 'post'">
          <span class="n-icon">▶️</span> 投稿 <span class="n-num">{{ posts.length }}</span>
        </div>
        <div class="n-tab" :class="{ active: activeTab === 'fav' }" @click="activeTab = 'fav'">
          <span class="n-icon">⭐</span> 收藏 <span class="n-num">0</span>
        </div>
      </div>

      <div class="n-stats">
        <div class="n-stat-item">
          <div class="n-stat-key">关注数</div>
          <div class="n-stat-val">{{ user.following_count || 0 }}</div>
        </div>
        <div class="n-stat-item">
          <div class="n-stat-key">粉丝数</div>
          <div class="n-stat-val">{{ user.followers_count || 0 }}</div>
        </div>
      </div>
    </div>

    <div class="s-content">
      <div v-if="activeTab === 'post' || activeTab === 'home'">
        <div class="sub-header">
          <h3>我的视频</h3>
          <div class="sub-filter">
            <span>最新发布</span>
            <span>最多播放</span>
          </div>
        </div>

        <div v-if="posts.length" class="bili-grid">
          <PostPreviewCard v-for="p in posts" :key="p.id" :post="p" />
        </div>

        <div v-else class="empty-state">
          <div class="empty-img">📺</div>
          <p>空空如也，去发一条动态吧~</p>
          <button v-if="isMe" class="btn-primary" type="button" @click="goNewPost">立即投稿</button>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-img">⭐</div>
        <p>收藏功能开发中...</p>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading-full">加载中...</div>

  <div v-else class="loading-full">
    <div class="error-box">
      <div class="error-title">{{ error || '加载失败' }}</div>
      <div class="error-tip">请检查链接是否正确（PID），或稍后重试。</div>
    </div>
  </div>
</template>

<style scoped>
.bili-space {
  background: #f4f5f7;
  min-height: 100vh;
  padding-bottom: 50px;
}

/* Header */
.h-inner {
  background: #fff;
  box-shadow: 0 0 0 1px #eee;
  padding-bottom: 16px;
}

.h-banner {
  height: 200px;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  background-color: #f1f2f3;
  position: relative;
}

.h-gradient {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 80px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.5), transparent);
  pointer-events: none;
}

.banner-edit-trigger {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  backdrop-filter: blur(4px);
  opacity: 0;
  transition: opacity 0.2s;
}

.h-banner:hover .banner-edit-trigger {
  opacity: 1;
}

.h-user-wrapper {
  max-width: 1284px;
  margin: 0 auto;
  position: relative;
  display: flex;
  padding: 0 20px;
}

.h-avatar {
  width: 100px;
  height: 100px;
  margin-top: -24px;
  border: 4px solid rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  background: #fff;
  overflow: hidden;
  z-index: 2;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.h-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  background: #f1f2f3;
  color: #6d757a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 700;
}

.h-info {
  margin-left: 20px;
  padding-top: 12px;
  flex: 1;
}

.h-basic {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.h-name {
  font-size: 22px;
  font-weight: 700;
  color: #18191c;
  line-height: 1.2;
}

.h-level {
  font-size: 12px;
  color: #fff;
  background: #f04c49;
  padding: 0 4px;
  border-radius: 2px;
  transform: scale(0.9);
}

.h-bio {
  font-size: 13px;
  color: #9499a0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 600px;
}

.h-action {
  padding-top: 16px;
  display: flex;
  gap: 12px;
}

.btn-primary {
  background: #00aeec;
  color: #fff;
  border: none;
  padding: 6px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #009cd6;
}

.btn-primary-ghost {
  border: 1px solid #00aeec;
  color: #00aeec;
  background: #fff;
  padding: 6px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary-ghost:hover {
  background: #f1f8ff;
}

.btn-ghost {
  border: 1px solid #ccd0d7;
  color: #6d757a;
  background: #fff;
  padding: 6px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-ghost:hover {
  border-color: #00aeec;
  color: #00aeec;
}

/* Navigator */
.n-inner {
  background: #fff;
  border-top: 1px solid #f1f2f3;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  max-width: 1284px;
  margin: 0 auto;
  padding: 0 20px;
  height: 66px;
}

.n-tab-list {
  display: flex;
  height: 100%;
  align-items: center;
}

.n-tab {
  margin-right: 30px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 15px;
  color: #18191c;
  height: 100%;
  position: relative;
  transition: color 0.2s;
}

.n-tab:hover {
  color: #00aeec;
}

.n-tab.active {
  color: #00aeec;
}

.n-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  height: 3px;
  background: #00aeec;
  border-radius: 2px;
}

.n-num {
  font-size: 12px;
  color: #9499a0;
  font-family: Arial;
}

.n-stats {
  margin-left: auto;
  display: flex;
  gap: 30px;
}

.n-stat-item {
  text-align: center;
  cursor: pointer;
}

.n-stat-item:hover .n-stat-key,
.n-stat-item:hover .n-stat-val {
  color: #00aeec;
}

.n-stat-key {
  font-size: 12px;
  color: #9499a0;
  margin-bottom: 2px;
}

.n-stat-val {
  font-size: 16px;
  color: #18191c;
  font-weight: 600;
}

/* Content */
.s-content {
  max-width: 1100px;
  margin: 0 auto;
  background: #fff;
  border-radius: 6px;
  padding: 20px;
  border: 1px solid #e3e5e7;
  min-height: 400px;
}

.sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e3e5e7;
}

.sub-header h3 {
  font-size: 20px;
  margin: 0;
  font-weight: 400;
}

.sub-filter span {
  font-size: 12px;
  color: #18191c;
  margin-left: 20px;
  cursor: pointer;
}

.sub-filter span:first-child {
  color: #00aeec;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: #9499a0;
}

.empty-img {
  font-size: 48px;
  margin-bottom: 10px;
  opacity: 0.5;
}

.loading-full {
  padding: 100px;
  text-align: center;
  color: #999;
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
</style>
