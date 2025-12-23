<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, unwrapList } from '../api'

const pendingPosts = ref([])
const pendingResources = ref([])
const loading = ref(false)
const error = ref('')

const postRejectReason = ref({})
const resourceRejectReason = ref({})
const busy = ref({})

const revisionsByPostId = ref({})
const selectedRevisionByPostId = ref({})
const diffByPostId = ref({})
const revBusy = ref({})

const pendingPostCount = computed(() => pendingPosts.value.length)
const pendingResourceCount = computed(() => pendingResources.value.length)

async function load() {
  error.value = ''
  loading.value = true
  try {
    const [p, r] = await Promise.all([
      api.get('/api/posts/moderation/pending/'),
      api.get('/api/resources/moderation/pending/'),
    ])
    pendingPosts.value = unwrapList(p.data)
    pendingResources.value = unwrapList(r.data)
  } catch (e) {
    error.value = '加载审核队列失败。'
  } finally {
    loading.value = false
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

async function approveResource(id) {
  busy.value[`res:${id}`] = true
  try {
    await api.post(`/api/resources/${id}/approve/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`res:${id}`] = false
  }
}

async function rejectResource(id) {
  busy.value[`res:${id}`] = true
  try {
    const reason = (resourceRejectReason.value[id] || '').trim()
    await api.post(`/api/resources/${id}/reject/`, { reason })
    resourceRejectReason.value[id] = ''
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[`res:${id}`] = false
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">审核队列</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>
      <div class="muted" style="margin-top: 6px">
        待审帖子 {{ pendingPostCount }} · 待审资源 {{ pendingResourceCount }}
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="card stack">
      <div class="row" style="justify-content: space-between">
        <h3 style="margin: 0">待审帖子（{{ pendingPosts.length }}）</h3>
        <button class="btn" :disabled="loading" @click="load">刷新</button>
      </div>
      <div v-for="p in pendingPosts" :key="p.id" class="card">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ p.title }}</div>
            <div class="muted">
              by {{ p.author_nickname || p.author_username }}
              <span v-if="p.author_nickname && p.author_username"> · {{ p.author_username }}</span>
              <span v-if="p.author_pid"> · PID {{ p.author_pid }}</span>
              · board={{ p.board_slug }} · 创建：{{ new Date(p.created_at).toLocaleString() }}
              <span v-if="p.updated_at"> · 最后编辑：{{ new Date(p.updated_at).toLocaleString() }}</span>
            </div>
            <div v-if="p.body" class="muted" style="margin-top: 6px">
              {{ String(p.body).slice(0, 120) }}<span v-if="String(p.body).length > 120">…</span>
            </div>
          </div>
          <div class="row">
            <RouterLink class="btn" :to="`/posts/${p.id}`">查看</RouterLink>
            <button class="btn" :disabled="busy[`post:${p.id}`]" @click="approvePost(p.id)">通过</button>
            <button class="btn" :disabled="busy[`post:${p.id}`]" @click="rejectPost(p.id)">拒绝</button>
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
              {{ new Date(rev.created_at).toLocaleString() }}
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

    <div class="card stack">
      <h3 style="margin: 0">待审资源（{{ pendingResources.length }}）</h3>
      <div v-for="r in pendingResources" :key="r.id" class="card">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ r.title }}</div>
            <div class="muted">
              by {{ r.created_by_nickname || r.created_by_username || '未知' }}
              <span v-if="r.created_by_nickname && r.created_by_username"> · {{ r.created_by_username }}</span>
              <span v-if="r.created_by_pid"> · PID {{ r.created_by_pid }}</span>
              · {{ new Date(r.created_at).toLocaleString() }}
            </div>
            <div class="muted" style="margin-top: 6px">
              关联帖子：
              <RouterLink v-if="r.post" class="btn" style="padding: 4px 8px" :to="`/posts/${r.post}`">#{{ r.post }}</RouterLink>
              <span v-else>-</span>
              <span style="margin-left: 10px">链接：{{ r.links?.length || 0 }}</span>
              <span v-if="r.links?.length" style="margin-left: 10px">
                （{{ r.links.map((x) => x.link_type).join(' / ') }}）
              </span>
            </div>
          </div>
          <div class="row">
            <button class="btn" :disabled="busy[`res:${r.id}`]" @click="approveResource(r.id)">通过</button>
            <button class="btn" :disabled="busy[`res:${r.id}`]" @click="rejectResource(r.id)">拒绝</button>
          </div>
        </div>

        <div class="row" style="margin-top: 10px">
          <input
            v-model="resourceRejectReason[r.id]"
            placeholder="拒绝原因（可选，最多200字）"
            maxlength="200"
          />
        </div>
      </div>
      <div v-if="pendingResources.length === 0" class="muted">暂无</div>
    </div>
  </div>
</template>
