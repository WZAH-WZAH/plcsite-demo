<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import { auth } from '../auth'

const route = useRoute()

const boards = ref([])
const posts = ref([])
const loading = ref(false)
const error = ref('')

const board = computed(() => boards.value.find((b) => b.slug === route.params.slug))

function statusText(s) {
  if (s === 'published') return '已发布'
  if (s === 'pending') return '待审核'
  if (s === 'rejected') return '已拒绝'
  return s || ''
}

async function loadBoards() {
  const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
  boards.value = unwrapList(data)
}

async function loadPosts() {
  if (!board.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet('/api/posts/', { __skipAuth: true, params: { board: board.value.id } }, 8000)
    posts.value = unwrapList(data)
  } catch (e) {
    error.value = '加载帖子失败。'
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    await loadBoards()
    if (!board.value) {
      error.value = '板块不存在。'
      return
    }
    await loadPosts()
  } catch (e) {
    error.value = '加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
watch(() => route.params.slug, loadAll)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <div>
          <h2 style="margin: 0 0 6px">{{ board?.title || '板块' }}</h2>
          <div class="muted">{{ board?.description || '浏览与发布内容' }}</div>
        </div>
        <div class="row">
          <RouterLink class="btn" to="/boards">返回</RouterLink>
          <RouterLink class="btn btn-primary" to="/posts/new">发帖</RouterLink>
        </div>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div v-if="loading" class="muted">加载中…</div>

    <div v-else class="stack">
      <RouterLink v-for="p in posts" :key="p.id" class="card" :to="`/posts/${p.id}`">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ p.title }}</div>
            <div class="muted">
              by {{ p.author_username }} · 创建：{{ new Date(p.created_at).toLocaleString() }}
              <span v-if="p.updated_at"> · 最后编辑：{{ new Date(p.updated_at).toLocaleString() }}</span>
            </div>
          </div>
          <div class="muted" v-if="auth.state.me">
            {{ statusText(p.status) }}
          </div>
        </div>
      </RouterLink>

      <div v-if="posts.length === 0" class="muted">暂无帖子</div>
    </div>
  </div>
</template>
