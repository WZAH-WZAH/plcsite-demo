<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiGet } from '../api'
import { auth } from '../auth'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { sanitizeHtml } from '../sanitize'

import PostActionBar from '../components/PostActionBar.vue'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const loading = ref(false)
const error = ref('')

const comments = ref([])
const commentsLoading = ref(false)
const commentsError = ref('')
const newComment = ref('')
const replyTargetId = ref(null)
const replyDraft = ref('')

const canEdit = computed(() => {
  const me = auth.state.me
  if (!me || !post.value) return false
  return me.username === post.value.author_username
})

const canFollowAuthor = computed(() => {
  const me = auth.state.me
  if (!me || !post.value) return false
  // Avoid self-follow.
  return me.username && post.value.author_username && me.username !== post.value.author_username
})

const canDelete = computed(() => {
  const me = auth.state.me
  if (!me || !post.value) return false
  return me.is_staff || me.username === post.value.author_username
})

const postAuthorNickname = computed(() => post.value?.author_nickname || '')
const postAuthorUsername = computed(() => post.value?.author_username || '')
const postAuthorDisplay = computed(() => postAuthorNickname.value || postAuthorUsername.value)

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (auth.isAuthed() && !auth.state.me && !auth.state.loading) {
      await auth.loadMe()
    }
    const { data } = await apiGet(`/api/posts/${route.params.id}/`, { __skipAuth: true }, 8000)
    post.value = data
    await loadComments()
  } catch (e) {
    error.value = '加载失败或无权限查看。'
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  if (!route.params.id) return
  commentsLoading.value = true
  commentsError.value = ''
  try {
    const { data } = await apiGet(`/api/posts/${route.params.id}/comments/`, { __skipAuth: true }, 8000)
    comments.value = Array.isArray(data) ? data : data?.results || []
  } catch (e) {
    commentsError.value = '评论加载失败。'
  } finally {
    commentsLoading.value = false
  }
}

const commentTree = computed(() => {
  const items = (comments.value || []).map((c) => ({ ...c, replies: [] }))
  const map = new Map(items.map((c) => [c.id, c]))
  const roots = []
  for (const c of items) {
    const pid = c.parent_id
    if (pid && map.has(pid)) {
      map.get(pid).replies.push(c)
    } else {
      roots.push(c)
    }
  }
  return roots
})

function canDeleteComment(c) {
  const me = auth.state.me
  if (!me || !c) return false
  return me.is_staff || me.username === c.author_username
}

async function submitComment(parentId = null) {
  if (!auth.isAuthed()) {
    commentsError.value = '请先登录后再发表评论。'
    return
  }
  const body = (parentId ? replyDraft.value : newComment.value) || ''
  if (!body.trim()) {
    commentsError.value = '评论内容不能为空。'
    return
  }

  commentsError.value = ''
  try {
    await api.post(`/api/posts/${route.params.id}/comments/`, {
      body,
      parent: parentId,
    })

    if (parentId) {
      replyTargetId.value = null
      replyDraft.value = ''
    } else {
      newComment.value = ''
    }
    await loadComments()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.response?.data?.body || '发表评论失败。'
    commentsError.value = Array.isArray(msg) ? msg.join('；') : String(msg)
  }
}

function startReply(commentId) {
  replyTargetId.value = commentId
  replyDraft.value = ''
}

async function deleteComment(commentId) {
  if (!commentId) return
  if (!confirm('确定要删除这条评论吗？')) return
  try {
    await api.delete(`/api/comments/${commentId}/`)
    await loadComments()
  } catch (e) {
    commentsError.value = e?.response?.data?.detail || '删除评论失败。'
  }
}

async function deletePost() {
  if (!post.value) return
  if (!confirm('确定要删除该帖子吗？此操作不可撤销。')) return
  try {
    await api.delete(`/api/posts/${post.value.id}/`)
    await router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || '删除失败。'
  }
}

async function toggleLike() {
  if (!post.value) return
  if (!auth.isAuthed()) {
    error.value = '请先登录后再点赞。'
    return
  }
  try {
    const { data } = await api.post(`/api/posts/${post.value.id}/like/`)
    post.value.is_liked = !!data.liked
    if (typeof data.likes_count === 'number') post.value.likes_count = data.likes_count
  } catch (e) {
    error.value = e?.response?.data?.detail || '点赞操作失败。'
  }
}

async function toggleFavorite() {
  if (!post.value) return
  if (!auth.isAuthed()) {
    error.value = '请先登录后再收藏。'
    return
  }
  try {
    const { data } = await api.post(`/api/posts/${post.value.id}/favorite/`)
    post.value.is_favorited = !!data.favorited
    if (typeof data.favorites_count === 'number') post.value.favorites_count = data.favorites_count
  } catch (e) {
    error.value = e?.response?.data?.detail || '收藏操作失败。'
  }
}

async function toggleFollowAuthor() {
  if (!post.value) return
  if (!auth.isAuthed()) {
    error.value = '请先登录后再关注作者。'
    return
  }
  if (!canFollowAuthor.value) return

  try {
    const { data } = await api.post(`/api/users/${post.value.author}/follow/`)
    post.value.is_following_author = !!data.following
  } catch (e) {
    error.value = e?.response?.data?.detail || '关注操作失败。'
  }
}

async function download(link) {
  try {
    const resourceId = post.value?.resource?.id
    if (!resourceId) return
    const { data } = await api.post(`/api/resources/${resourceId}/links/${link.id}/download/`)
    window.open(data.url, '_blank', 'noopener,noreferrer')
  } catch (e) {
    error.value = e?.response?.data?.detail || '下载失败。'
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <div>
          <h2 style="margin: 0 0 6px">{{ post?.title || '帖子' }}</h2>
          <div class="muted" v-if="post">
            by {{ postAuthorDisplay }}
            <template v-if="postAuthorNickname && postAuthorUsername"> · {{ postAuthorUsername }}</template>
            · 创建：{{ new Date(post.created_at).toLocaleString() }}
            <span v-if="post.updated_at"> · 最后编辑：{{ new Date(post.updated_at).toLocaleString() }}</span>
          </div>
        </div>
        <div class="row">
          <button v-if="post" class="btn" type="button" @click="toggleLike">
            {{ post.is_liked ? '已赞' : '点赞' }} ({{ post.likes_count || 0 }})
          </button>
          <button v-if="post" class="btn" type="button" @click="toggleFavorite">
            {{ post.is_favorited ? '已收藏' : '收藏' }} ({{ post.favorites_count || 0 }})
          </button>
          <button v-if="post && canFollowAuthor" class="btn" type="button" @click="toggleFollowAuthor">
            {{ post.is_following_author ? '已关注' : '关注作者' }}
          </button>
          <RouterLink class="btn" to="/">返回</RouterLink>
          <RouterLink v-if="canEdit" class="btn" :to="`/posts/${post.id}/edit`">编辑</RouterLink>
          <button v-if="canDelete" class="btn" type="button" @click="deletePost">删除</button>
        </div>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <div v-if="post" class="card">
      <img
        v-if="post.cover_image_url"
        :src="post.cover_image_url"
        alt="cover"
        style="max-width: 100%; border-radius: 10px; margin-bottom: 12px"
      />
      <MdPreview :modelValue="post.body" :sanitize="sanitizeHtml" />

      <PostActionBar :post="post" :isDetail="true" />
    </div>

    <div v-if="post?.resource?.links?.length" class="card stack">
      <h3 style="margin: 0">资源链接</h3>
      <div class="row" v-for="l in post.resource.links" :key="l.id">
        <span class="muted" style="min-width: 90px">{{ l.link_type }}</span>
        <button class="btn" @click="download(l)">下载</button>
      </div>
      <div class="muted" style="font-size: 12px">下载会计入每日下载配额。</div>
    </div>

    <div v-if="post" id="comments" class="card stack">
      <div class="row" style="justify-content: space-between">
        <h3 style="margin: 0">评论</h3>
        <button class="btn" type="button" @click="loadComments" :disabled="commentsLoading">刷新</button>
      </div>

      <div v-if="commentsError" class="muted" style="color: #b91c1c">{{ commentsError }}</div>

      <div class="stack" v-if="auth.isAuthed()">
        <textarea v-model="newComment" rows="3" placeholder="写下你的评论…"></textarea>
        <div class="row">
          <button class="btn" type="button" @click="submitComment(null)">发表评论</button>
        </div>
      </div>
      <div v-else class="muted">登录后可发表评论。</div>

      <div v-if="commentsLoading" class="muted">评论加载中…</div>
      <div v-else-if="!comments.length" class="muted">还没有评论。</div>

      <div v-else class="stack">
        <div v-for="c in commentTree" :key="c.id" class="card" style="background: #fafafa">
          <div class="row" style="justify-content: space-between">
            <div class="muted" style="font-size: 12px">
              {{ c.author_nickname || c.author_username }}
              <template v-if="c.author_nickname && c.author_username"> · {{ c.author_username }}</template>
              · {{ new Date(c.created_at).toLocaleString() }}
              <span v-if="c.is_deleted"> · 已删除</span>
            </div>
            <div class="row" style="gap: 8px">
              <button class="btn" type="button" @click="startReply(c.id)" :disabled="!auth.isAuthed()">回复</button>
              <button v-if="canDeleteComment(c)" class="btn" type="button" @click="deleteComment(c.id)">删除</button>
            </div>
          </div>

          <div v-if="c.is_deleted" class="muted">（该评论已删除）</div>
          <MdPreview v-else :modelValue="c.body" :sanitize="sanitizeHtml" />

          <div v-if="replyTargetId === c.id" class="stack" style="margin-top: 10px">
            <textarea v-model="replyDraft" rows="2" placeholder="写下回复…"></textarea>
            <div class="row">
              <button class="btn" type="button" @click="submitComment(c.id)">发送回复</button>
              <button class="btn" type="button" @click="replyTargetId = null">取消</button>
            </div>
          </div>

          <div v-if="c.replies?.length" class="stack" style="margin-top: 10px">
            <div v-for="r in c.replies" :key="r.id" class="card" style="background: #ffffff">
              <div class="row" style="justify-content: space-between">
                <div class="muted" style="font-size: 12px">
                  {{ r.author_nickname || r.author_username }}
                  <template v-if="r.author_nickname && r.author_username"> · {{ r.author_username }}</template>
                  · {{ new Date(r.created_at).toLocaleString() }}
                  <span v-if="r.is_deleted"> · 已删除</span>
                </div>
                <button v-if="canDeleteComment(r)" class="btn" type="button" @click="deleteComment(r.id)">删除</button>
              </div>

              <div v-if="r.is_deleted" class="muted">（该回复已删除）</div>
              <MdPreview v-else :modelValue="r.body" :sanitize="sanitizeHtml" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
