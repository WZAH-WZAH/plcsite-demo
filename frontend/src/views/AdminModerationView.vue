<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, unwrapList } from '../api'
import { auth } from '../auth'
import { fmtDateTime } from '../datetime'

const pendingPosts = ref([])
const boards = ref([])
const loading = ref(false)
const error = ref('')

const mineOnly = ref(true)
const boardSlug = ref('all')

const postRejectReason = ref({})
const busy = ref({})

const revisionsByPostId = ref({})
const selectedRevisionByPostId = ref({})
const diffByPostId = ref({})
const revBusy = ref({})

const pendingPostCount = computed(() => pendingPosts.value.length)

const me = computed(() => auth.state.me)

function isClaimedByMe(p) {
  return Boolean(p?.claimed_by_id && me.value?.id && p.claimed_by_id === me.value.id)
}

function isClaimedByOther(p) {
  return Boolean(p?.claimed_by_id && me.value?.id && p.claimed_by_id !== me.value.id)
}

function canActOnPost(p) {
  if (me.value?.is_superuser) return true
  if (!p?.can_moderate) return false
  if (isClaimedByOther(p)) return false
  return true
}

async function loadBoards() {
  try {
    const { data } = await api.get('/api/boards/')
    boards.value = unwrapList(data).filter((b) => b?.is_active)
  } catch {
    boards.value = []
  }
}

async function load() {
  error.value = ''
  loading.value = true
  try {
    const params = {
      mine: mineOnly.value ? 1 : 0,
    }
    if (boardSlug.value && boardSlug.value !== 'all') params.board_slug = boardSlug.value
    const { data } = await api.get('/api/posts/moderation/pending/', { params })
    pendingPosts.value = unwrapList(data)
  } catch (e) {
    error.value = '加载审核队列失败。'
  } finally {
    loading.value = false
  }
}

async function claimPost(id) {
  busy.value[`claim:${id}`] = true
  try {
    await api.post(`/api/posts/${id}/moderation/claim/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`claim:${id}`] = false
  }
}

async function unclaimPost(id) {
  busy.value[`unclaim:${id}`] = true
  try {
    await api.post(`/api/posts/${id}/moderation/unclaim/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`unclaim:${id}`] = false
  }
}

async function approvePost(id) {
  busy.value[`post:${id}`] = true
  try {
    await api.post(`/api/posts/${id}/approve/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`post:${id}`] = false
  }
}

async function rejectPost(id) {
  busy.value[`post:${id}`] = true
  try {
    const reason = (postRejectReason.value[id] || '').trim()
    await api.post(`/api/posts/${id}/reject/`, { reason })
    postRejectReason.value[id] = ''
    // 清理本地缓存
    delete revisionsByPostId.value[id]
    delete selectedRevisionByPostId.value[id]
    delete diffByPostId.value[id]
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`post:${id}`] = false
  }
}

async function loadRevisions(postId) {
  revBusy.value[`revs:${postId}`] = true
  try {
    const { data } = await api.get(`/api/posts/${postId}/revisions/`)
    revisionsByPostId.value[postId] = unwrapList(data)
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载编辑记录失败。'
  } finally {
    revBusy.value[`revs:${postId}`] = false
  }
}

async function loadDiff(postId, revisionId) {
  selectedRevisionByPostId.value[postId] = revisionId
  revBusy.value[`diff:${postId}`] = true
  try {
    const { data } = await api.get(`/api/posts/${postId}/revisions/${revisionId}/diff`)
    diffByPostId.value[postId] = data?.diff || ''
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载 diff 失败。'
  } finally {
    revBusy.value[`diff:${postId}`] = false
  }
}

onMounted(async () => {
  if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
    await auth.loadMe()
  }
  await loadBoards()
  await load()
})
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">审核队列</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>
      <div class="row" style="margin-top: 10px; flex-wrap: wrap; gap: 10px">
        <label class="row" style="gap: 6px">
          <input v-model="mineOnly" type="checkbox" @change="load" />
          <span class="muted">只显示你的待审核（默认勾选）</span>
        </label>

        <div class="row" style="gap: 8px">
          <span class="muted">板块</span>
          <select v-model="boardSlug" @change="load">
            <option value="all">全部</option>
            <option v-for="b in boards" :key="b.id" :value="b.slug">{{ b.title }}</option>
          </select>
        </div>

        <button class="btn" :disabled="loading" @click="load">刷新</button>
      </div>

      <div class="muted" style="margin-top: 6px">待审帖子 {{ pendingPostCount }}</div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="card stack">
      <div class="row" style="justify-content: space-between">
        <h3 style="margin: 0">待审帖子（{{ pendingPosts.length }}）</h3>
        <div class="muted" style="font-size: 12px">支持“占用”避免多人重复处理</div>
      </div>
      <div v-for="p in pendingPosts" :key="p.id" class="card">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ p.title }}</div>
            <div class="muted">
              作者：{{ p.author_nickname || p.author_username }}
              <span v-if="p.author_nickname && p.author_username"> · {{ p.author_username }}</span>
              <span v-if="p.author_pid"> · PID {{ p.author_pid }}</span>
              · 板块={{ p.board_slug }} · 创建：{{ fmtDateTime(p.created_at) }}
              <span v-if="p.updated_at"> · 最后编辑：{{ fmtDateTime(p.updated_at) }}</span>
            </div>

            <div class="muted" style="margin-top: 6px">
              <span v-if="p.claimed_by_id">
                占用中：{{ p.claimed_by_nickname || p.claimed_by_username || '未知' }}
                <span v-if="p.claimed_by_pid"> · PID {{ p.claimed_by_pid }}</span>
                <span v-if="isClaimedByMe(p)"> · （你）</span>
              </span>
              <span v-else>未占用</span>
              <span v-if="!p.can_moderate && !me?.is_superuser"> · 你没有此板块审核权限</span>
            </div>

            <div v-if="p.body" class="muted" style="margin-top: 6px">
              {{ String(p.body).slice(0, 120) }}<span v-if="String(p.body).length > 120">…</span>
            </div>
          </div>
          <div class="row">
            <RouterLink class="btn" :to="`/posts/${p.id}`">查看</RouterLink>

            <button
              v-if="!p.claimed_by_id"
              class="btn"
              :disabled="busy[`claim:${p.id}`] || !p.can_moderate"
              @click="claimPost(p.id)"
            >
              占用
            </button>
            <button
              v-else
              class="btn"
              :disabled="busy[`unclaim:${p.id}`] || (!isClaimedByMe(p) && !me?.is_superuser)"
              @click="unclaimPost(p.id)"
            >
              释放
            </button>

            <button class="btn" :disabled="busy[`post:${p.id}`] || !canActOnPost(p)" @click="approvePost(p.id)">
              通过
            </button>
            <button class="btn" :disabled="busy[`post:${p.id}`] || !canActOnPost(p)" @click="rejectPost(p.id)">
              拒绝
            </button>
          </div>
        </div>

        <div class="row" style="margin-top: 10px">
          <input
            v-model="postRejectReason[p.id]"
            placeholder="拒绝原因（可选，最多200字）"
            maxlength="200"
          />
        </div>

        <div class="card stack" style="margin-top: 10px">
          <div class="row" style="justify-content: space-between">
            <div>
              <div style="font-weight: 700">编辑记录</div>
              <div class="muted" style="font-size: 12px">点击某条记录查看该次改动 diff</div>
            </div>
            <button
              class="btn"
              type="button"
              :disabled="revBusy[`revs:${p.id}`]"
              @click="loadRevisions(p.id)"
            >
              {{ revBusy[`revs:${p.id}`] ? '加载中…' : '加载' }}
            </button>
          </div>

          <div v-if="revisionsByPostId[p.id]?.length" class="row" style="flex-wrap: wrap; gap: 8px">
            <button
              v-for="rev in revisionsByPostId[p.id]"
              :key="rev.id"
              class="btn"
              type="button"
              :disabled="revBusy[`diff:${p.id}`]"
              @click="loadDiff(p.id, rev.id)"
            >
              {{ fmtDateTime(rev.created_at) }}
              <span v-if="rev.editor_username"> · {{ rev.editor_username }}</span>
            </button>
          </div>

          <div v-if="selectedRevisionByPostId[p.id] && diffByPostId[p.id]" class="card" style="padding: 10px">
            <div class="muted" style="font-size: 12px; margin-bottom: 6px">unified diff</div>
            <pre style="white-space: pre-wrap; margin: 0">{{ diffByPostId[p.id] }}</pre>
          </div>

          <div v-else-if="revisionsByPostId[p.id] && revisionsByPostId[p.id].length === 0" class="muted">暂无编辑记录</div>
        </div>
      </div>
      <div v-if="pendingPosts.length === 0" class="muted">暂无</div>
    </div>
  </div>
</template>
