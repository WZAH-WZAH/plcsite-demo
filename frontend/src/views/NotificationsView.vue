<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, unwrapList } from '../api'
import { auth } from '../auth'

const loading = ref(false)
const error = ref('')
const items = ref([])

const isAuthed = computed(() => auth.isAuthed())

async function load() {
  if (!isAuthed.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/notifications/')
    items.value = unwrapList(data)
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载通知失败。'
  } finally {
    loading.value = false
  }
}

async function markAllRead() {
  try {
    await api.post('/api/notifications/mark-all-read/')
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  }
}

function formatType(t) {
  if (t === 'reply_to_comment') return '回复了你的评论'
  if (t === 'comment_on_post') return '评论了你的帖子'
  return t
}

onMounted(async () => {
  if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
    await auth.loadMe()
  }
  await load()
})
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">通知</h2>
        <div class="row">
          <button class="btn" type="button" @click="load" :disabled="loading">刷新</button>
          <button class="btn" type="button" @click="markAllRead" :disabled="loading">全部已读</button>
        </div>
      </div>
    </div>

    <div v-if="!isAuthed" class="card">请先登录后查看通知。</div>
    <div v-else>
      <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>
      <div v-if="loading" class="muted">加载中…</div>

      <div v-else-if="!items.length" class="card muted">暂无通知。</div>

      <div v-else class="stack">
        <div v-for="n in items" :key="n.id" class="card">
          <div class="row" style="justify-content: space-between">
            <div>
              <div style="font-weight: 600">
                <span v-if="!n.is_read">[未读]</span>
                {{ formatType(n.type) }}
              </div>
              <div class="muted" style="font-size: 12px">
                {{ n.actor_username || '系统' }} · {{ new Date(n.created_at).toLocaleString() }}
              </div>
            </div>
            <RouterLink class="btn" :to="`/posts/${n.post}`">查看帖子</RouterLink>
          </div>

          <div class="muted" style="margin-top: 6px">{{ n.post_title }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
