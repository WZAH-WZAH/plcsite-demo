<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()
const user = ref(null)
const posts = ref([])
const loading = ref(true)

async function loadData() {
  loading.value = true
  const username = route.params.username
  try {
    user.value = {
      username: username,
      avatar: `https://api.dicebear.com/7.x/miniavs/svg?seed=${username}`,
      banner:
        'https://i0.hdslb.com/bfs/space/cb1c3ef50e22b6096fde67febe863494caefebad.png@2560w_400h_100q_1o.webp',
      bio: '这个人很懒，什么都没有写',
      following: 42,
      fans: 108,
    }

    const { data } = await apiGet('/api/posts/', { params: { author_username: username }, __skipAuth: true })
    posts.value = unwrapList(data)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => route.params.username, loadData)
</script>

<template>
  <div v-if="user" class="space-container">
    <div class="space-banner" :style="{ backgroundImage: `url(${user.banner})` }">
      <div class="banner-gradient"></div>
      <div class="user-info-wrapper">
        <div class="avatar-holder">
          <img :src="user.avatar" class="big-avatar" />
        </div>
        <div class="text-info">
          <div class="name-row">
            <span class="name">{{ user.username }}</span>
            <span class="level-tag">Lv6</span>
          </div>
          <div class="bio">{{ user.bio }}</div>
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
            <div class="stat-val">{{ user.following }}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">粉丝数</div>
            <div class="stat-val">{{ user.fans }}</div>
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
</template>

<style scoped>
.space-container {
  background: #fff;
  min-height: 100vh;
}

/* Banner */
.space-banner {
  height: 200px;
  background-size: cover;
  background-position: center;
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
.text-info {
  margin-bottom: 30px;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
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
