<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiGet } from '../api'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'

import PostActionBar from '../components/PostActionBar.vue'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const loading = ref(false)
const error = ref('')

async function fetchPost() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet(`/api/posts/${route.params.id}/`)
    post.value = data
  } catch (err) {
    error.value = '无法加载帖子详情'
  } finally {
    loading.value = false
  }
}

// 优先显示昵称
const displayName = computed(() => post.value?.author_nickname || post.value?.author_username)
const authorPid = computed(() => post.value?.author_pid)

function goToProfile() {
  if (authorPid.value) router.push(`/u/${authorPid.value}`)
}

onMounted(fetchPost)
</script>

<template>
  <div class="article-container">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <div v-else-if="post" class="article-content">
      <h1 class="article-title">{{ post.title }}</h1>

      <div class="author-row">
        <div class="avatar-box" @click="goToProfile">
          <img v-if="post.author_avatar" :src="post.author_avatar" />
          <span v-else>{{ displayName?.[0]?.toUpperCase() }}</span>
        </div>
        <div class="meta-box">
          <div class="author-name" @click="goToProfile">{{ displayName }}</div>
          <div class="publish-info">
            {{ new Date(post.created_at).toLocaleString() }}
            <span v-if="post.board_title"> · {{ post.board_title }}</span>
          </div>
        </div>
      </div>

      <div v-if="post.cover_image_url" class="hero-image">
        <img :src="post.cover_image_url" />
      </div>

      <div class="markdown-body">
        <MdPreview :modelValue="post.body" />
      </div>

      <PostActionBar :post="post" :isDetail="true" />

      <div id="comments" class="comment-section">
        <h3 class="section-title">评论</h3>
        <div class="empty-comment">评论功能开发中...</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.article-container {
  width: 100%;
  min-height: 100vh;
  background: #fff;
  padding-bottom: 100px;
}

/* 核心：限制宽度，居中阅读 */
.article-content {
  max-width: 680px;
  margin: 0 auto;
  padding: 40px 20px;
}

.article-title {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.4;
  color: #111827;
  margin-bottom: 24px;
  letter-spacing: -0.01em;
}

.author-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.avatar-box {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  overflow: hidden;
  background: #e5e7eb;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #6b7280;
}

.avatar-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.meta-box {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.author-name {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  cursor: pointer;
}

.author-name:hover {
  text-decoration: underline;
}

.publish-info {
  font-size: 13px;
  color: #6b7280;
  margin-top: 2px;
}

.hero-image {
  width: 100%;
  margin-bottom: 32px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.hero-image img {
  width: 100%;
  display: block;
}

/* 正文优化 */
.markdown-body {
  font-size: 18px;
  line-height: 1.8;
  color: #1f2937;
  margin-bottom: 48px;
}

.comment-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid #f3f4f6;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 20px;
}

.empty-comment {
  color: #9ca3af;
  text-align: center;
  padding: 40px;
  background: #f9fafb;
  border-radius: 8px;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 60px;
  color: #6b7280;
}

.error-state {
  color: #ef4444;
}
</style>
