<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiGet, unwrapList } from '../api'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'

import PostActionBar from '../components/PostActionBar.vue'
import { auth } from '../auth'
import { ui } from '../ui'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const loading = ref(false)
const error = ref('')

const commentsLoading = ref(false)
const commentsError = ref('')
const comments = ref([])

const commentText = ref('')
const submitting = ref(false)

const replyToId = ref(null)
const replyToName = ref('')

const CONTROL_CHAR_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/

function validateCommentBody(raw) {
  const text = String(raw || '')
  if (!text.trim()) return '请输入评论内容。'
  if (text.length > 20000) return '评论内容过长。'
  // Control special chars; allow newline and standard unicode (incl. 颜文字)
  if (CONTROL_CHAR_RE.test(text)) return '包含不支持的特殊字符。'
  // Match backend convention used in several places
  if (text.includes('<') || text.includes('>')) return '不允许包含 < 或 >。'
  return ''
}

async function fetchPost() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet(`/api/posts/${route.params.id}/`)
    post.value = data
    await loadComments()
  } catch (err) {
    error.value = '无法加载帖子详情'
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  if (!route.params.id) return
  commentsLoading.value = true
  commentsError.value = ''
  try {
    const { data } = await apiGet(`/api/posts/${route.params.id}/comments/`, { __skipAuth: true })
    comments.value = unwrapList(data)
  } catch (e) {
    commentsError.value = e?.response?.data?.detail || '加载评论失败。'
    comments.value = []
  } finally {
    commentsLoading.value = false
  }
}

function startReply(c) {
  replyToId.value = c?.id ?? null
  replyToName.value = String(c?.author_nickname || c?.author_username || '')
  const el = document.getElementById('comment-input')
  el?.focus?.()
}

function cancelReply() {
  replyToId.value = null
  replyToName.value = ''
}

async function submitComment() {
  if (!auth.isAuthed()) {
    router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  if (!post.value?.id) return
  if (submitting.value) return

  const errMsg = validateCommentBody(commentText.value)
  if (errMsg) {
    ui.openModal(errMsg, { title: '提示' })
    return
  }

  submitting.value = true
  try {
    const payload = {
      body: commentText.value,
      parent: replyToId.value || null,
    }
    await api.post(`/api/posts/${post.value.id}/comments/`, payload)
    commentText.value = ''
    cancelReply()
    await loadComments()
  } catch (e) {
    ui.openModal(e?.response?.data?.detail || '发表评论失败。', { title: '提示' })
  } finally {
    submitting.value = false
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

        <div class="comment-box">
          <div v-if="replyToId" class="reply-banner">
            正在回复 <span style="font-weight: 700">{{ replyToName || 'TA' }}</span>
            <button type="button" class="btn" style="margin-left: 10px" @click="cancelReply">取消</button>
          </div>

          <textarea
            id="comment-input"
            v-model="commentText"
            class="comment-input"
            rows="4"
            placeholder="写下你的评论（支持颜文字）"
          ></textarea>
          <div class="row" style="justify-content: flex-end; margin-top: 10px">
            <button class="btn btn-primary" type="button" :disabled="submitting" @click="submitComment">
              {{ submitting ? '发布中…' : '发表评论' }}
            </button>
          </div>
        </div>

        <div v-if="commentsLoading" class="muted" style="text-align: center; padding: 16px">加载评论中…</div>
        <div v-else-if="commentsError" class="muted" style="text-align: center; padding: 16px">{{ commentsError }}</div>

        <div v-else-if="!comments.length" class="empty-comment">暂无评论，快来抢沙发。</div>

        <div v-else class="comment-list">
          <div
            v-for="c in comments"
            :key="c.id"
            class="comment-item"
            :class="{ reply: !!c.parent_id }"
          >
            <div class="comment-meta">
              <span style="font-weight: 700">{{ c.author_nickname || c.author_username }}</span>
              <span class="dot">·</span>
              <span class="muted" style="font-size: 12px">{{ new Date(c.created_at).toLocaleString() }}</span>
            </div>
            <div v-if="c.is_deleted" class="muted">该评论已删除</div>
            <div v-else class="comment-body">
              <MdPreview :modelValue="c.body" />
            </div>
            <div v-if="!c.is_deleted" class="comment-actions">
              <button class="btn" type="button" @click="startReply(c)">回复</button>
            </div>
          </div>
        </div>
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

.comment-box {
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}

.reply-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 10px;
}

.comment-input {
  width: 100%;
  resize: vertical;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  font-size: 14px;
  line-height: 1.6;
  outline: none;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-item {
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 12px;
  background: #ffffff;
}

.comment-item.reply {
  margin-left: 18px;
  border-left: 3px solid #e5e7eb;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.dot {
  color: #9ca3af;
}

.comment-body :deep(.md-editor-preview) {
  padding: 0;
}

.comment-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
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
