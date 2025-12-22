<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import { auth } from '../auth'

const posts = ref([])
const loading = ref(false)
const error = ref('')

function statusText(s) {
  if (s === 'published') return '已发布'
  if (s === 'pending') return '待审核'
  if (s === 'rejected') return '已拒绝'
  return s || ''
}

function fmtTime(s) {
  try {
    return new Date(s).toLocaleString()
  } catch {
    return ''
  }
}

function stripMarkdown(text) {
  const t = (text || '').toString()
  if (!t) return ''
  // minimal cleanup for excerpts (avoid rendering markdown here)
  return t
    .replaceAll(/```[\s\S]*?```/g, '')
    .replaceAll(/`[^`]*`/g, '')
    .replaceAll(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replaceAll(/\[[^\]]*\]\([^)]*\)/g, '$1')
    .replaceAll(/#+\s+/g, '')
    .replaceAll(/[*_~>]/g, '')
    .replaceAll(/\n+/g, ' ')
    .trim()
}

function excerpt(text, n = 180) {
  const s = stripMarkdown(text)
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}

async function loadPosts() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true }, 8000)
    posts.value = unwrapList(data)
  } catch (e) {
    error.value = '加载帖子失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadPosts)
</script>

<template>
  <div class="stack">
    <div class="home-head">
      <div>
        <h2 class="home-title">最近更新</h2>
        <div class="muted">按更新时间浏览最新内容（时间线）</div>
      </div>
      <div class="row">
        <RouterLink class="btn" to="/">返回</RouterLink>
        <RouterLink class="btn btn-primary" to="/posts/new">发帖</RouterLink>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div v-if="loading" class="muted">加载中…</div>

    <div v-else class="timeline">
      <RouterLink v-for="p in posts" :key="p.id" class="timeline-item" :to="`/posts/${p.id}`">
        <div class="timeline-main">
          <div class="timeline-meta">
            <span style="font-weight: 700">{{ p.author_username }}</span>
            <span class="muted">· {{ fmtTime(p.updated_at || p.created_at) }}</span>
            <span class="muted" v-if="p.board_slug">· {{ p.board_slug }}</span>
            <span class="muted" v-if="auth.state.me">· {{ statusText(p.status) }}</span>
          </div>
          <div class="timeline-title">{{ p.title }}</div>
          <div v-if="p.body" class="timeline-excerpt muted">{{ excerpt(p.body) }}</div>
          <div class="timeline-cta">查看全文</div>
        </div>

        <div v-if="p.cover_image_url" class="timeline-media">
          <img :src="p.cover_image_url" alt="cover" />
        </div>
      </RouterLink>

      <div v-if="posts.length === 0" class="muted">暂无帖子</div>
    </div>
  </div>
</template>
