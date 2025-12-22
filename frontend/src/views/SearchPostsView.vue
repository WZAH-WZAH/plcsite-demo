<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const route = useRoute()
const router = useRouter()

const q = computed(() => (route.query.q || '').toString().trim())

const posts = ref([])
const facets = ref({ board_slug: {}, author_username: {} })
const loading = ref(false)
const error = ref('')

// -----------------
// Highlight helpers
// -----------------
// We intentionally do NOT render any HTML returned by the backend/search engine.
// Instead, we escape text and insert our own <mark> tags based on match positions.
function escapeHtml(s) {
  return (s || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderWithMatches(text, matches) {
  const raw = (text || '').toString()
  const ranges = []
  // Meilisearch returns: _matchesPosition: { title: [{start,length}], body: [...] }
  if (Array.isArray(matches)) {
    for (const m of matches) {
      const s = Number(m?.start)
      const l = Number(m?.length)
      if (Number.isFinite(s) && Number.isFinite(l) && l > 0) ranges.push([s, s + l])
    }
  }
  if (ranges.length === 0) return escapeHtml(raw)

  ranges.sort((a, b) => a[0] - b[0])
  // Merge overlaps
  const merged = []
  for (const r of ranges) {
    const last = merged[merged.length - 1]
    if (!last || r[0] > last[1]) merged.push(r)
    else last[1] = Math.max(last[1], r[1])
  }

  let out = ''
  let cursor = 0
  for (const [s, e] of merged) {
    const ss = Math.max(0, Math.min(s, raw.length))
    const ee = Math.max(0, Math.min(e, raw.length))
    if (ss > cursor) out += escapeHtml(raw.slice(cursor, ss))
    out += `<mark>${escapeHtml(raw.slice(ss, ee))}</mark>`
    cursor = ee
  }
  if (cursor < raw.length) out += escapeHtml(raw.slice(cursor))
  return out
}

function getTitleHtml(p) {
  const mp = p?._matchesPosition
  const matches = mp?.title
  return renderWithMatches(p?.title || '', matches)
}

function statusText(s) {
  if (s === 'published') return '已发布'
  if (s === 'pending') return '待审核'
  if (s === 'rejected') return '已拒绝'
  return s || ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (!q.value) {
      posts.value = []
      facets.value = { board_slug: {}, author_username: {} }
      return
    }
    const { data } = await api.get('/api/posts/search/', { params: { q: q.value, limit: 50, offset: 0 } })
    posts.value = Array.isArray(data?.hits) ? data.hits : []
    facets.value = data?.facets || { board_slug: {}, author_username: {} }
  } catch (e) {
    error.value = '搜索失败。'
  } finally {
    loading.value = false
  }
}

function clearSearch() {
  router.replace({ name: 'search', query: {} })
}

function applyFacet(kind, value) {
  if (!value) return
  const cur = q.value || ''
  const token = `${kind}:${value}`
  const next = cur.includes(token) ? cur : (cur ? `${cur} ${token}` : token)
  router.push({ name: 'search', query: next ? { q: next } : {} })
}

onMounted(load)
watch(() => route.query.q, load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <div>
          <h2 style="margin: 0 0 6px">搜索</h2>
          <div class="muted">关键词：{{ q || '（空）' }}</div>
        </div>
        <div class="row">
          <RouterLink class="btn" to="/">返回</RouterLink>
          <button v-if="q" class="btn" type="button" @click="clearSearch">清空</button>
        </div>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div v-if="loading" class="muted">加载中…</div>

    <div v-else class="stack">
      <div v-if="q" class="card stack">
        <div class="muted" style="font-size: 12px">聚合</div>
        <div class="row" style="flex-wrap: wrap">
          <span class="muted" style="min-width: 60px">板块：</span>
          <button
            v-for="(c, slug) in (facets.board_slug || {})"
            :key="`b-${slug}`"
            class="btn"
            type="button"
            @click="applyFacet('board', slug)"
          >
            {{ slug }} ({{ c }})
          </button>
        </div>
        <div class="row" style="flex-wrap: wrap">
          <span class="muted" style="min-width: 60px">作者：</span>
          <button
            v-for="(c, u) in (facets.author_username || {})"
            :key="`u-${u}`"
            class="btn"
            type="button"
            @click="applyFacet('author', u)"
          >
            {{ u }} ({{ c }})
          </button>
        </div>
        <div class="muted" style="font-size: 12px">
          高级搜索示例：<span>board:tools author:alice status:published is:locked</span>
        </div>
      </div>

      <RouterLink v-for="p in posts" :key="p.id" class="card" :to="`/posts/${p.id}`">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700" v-html="getTitleHtml(p)"></div>
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

      <div v-if="q && posts.length === 0" class="muted">没有匹配结果</div>
      <div v-if="!q" class="muted">在顶部输入关键词开始搜索</div>
    </div>
  </div>
</template>
