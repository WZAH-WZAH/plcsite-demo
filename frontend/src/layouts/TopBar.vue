<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useRouter } from 'vue-router'
import { auth } from '../auth'
import { api, apiGet, unwrapList } from '../api'

const searchText = ref('')
const router = useRouter()
const boards = ref([])
const boardsLoading = ref(false)
const unread = ref(0)

// Autocomplete state
const suggestOpen = ref(false)
const suggestLoading = ref(false)
const suggestions = ref([])
let suggestTimer = null

// Canonical nav order (matches product requirement)
// Notes:
// - “首页 / 最近更新”是导航入口，不属于可发帖板块。
// - 板块按 slug 映射，实际数据由后端迁移确保存在。
// - “公告/站务”放在二级导航右侧。
const canonicalBoardSlugs = ['games', 'mmd', 'irl', 'tech', 'daily']
const canonicalBoards = computed(() => {
  const bySlug = new Map(
    (boards.value || []).map((b) => [String(b?.slug || '').trim().toLowerCase(), b])
  )
  return canonicalBoardSlugs.map((slug) => bySlug.get(String(slug).toLowerCase())).filter(Boolean)
})

const bySlug = computed(
  () => new Map((boards.value || []).map((b) => [String(b?.slug || '').trim().toLowerCase(), b]))
)

const announcementsBoard = computed(() => bySlug.value.get('announcements') || { slug: 'announcements', title: '公告' })
const feedbackBoard = computed(() => bySlug.value.get('feedback') || { slug: 'feedback', title: '建议/反馈' })
const siteLogBoard = computed(() => bySlug.value.get('site-log') || { slug: 'site-log', title: '站务日志' })
const blackRoomBoard = computed(() => bySlug.value.get('blackroom') || { slug: 'blackroom', title: '小黑屋' })



// Avatar modal state
const avatarOpen = ref(false)
const avatarLoading = ref(false)
const avatarError = ref('')
const avatarInfo = ref(null)
const avatarFile = ref(null)
const avatarPreviewUrl = ref('')

const meAvatarUrl = computed(() => auth.state.me?.avatar_url || '')
const meInitial = computed(() => {
  const n = (auth.state.me?.nickname || '').trim()
  const u = (auth.state.me?.username || '').trim()
  const s = n || u
  return s ? s.slice(0, 1).toUpperCase() : 'U'
})

onMounted(async () => {
  boardsLoading.value = true
  try {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 15000)
    boards.value = unwrapList(data)
  } catch {
    // One retry to tolerate backend cold-start / brief network hiccups.
    try {
      const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 15000)
      boards.value = unwrapList(data)
    } catch {
      boards.value = []
    }
  } finally {
    boardsLoading.value = false
  }
})

async function loadUnread() {
  if (!auth.isAuthed()) {
    unread.value = 0
    return
  }
  try {
    const { data } = await api.get('/api/notifications/unread-count/')
    unread.value = Number(data?.unread || 0)
  } catch {
    // ignore
  }
}

watch(
  () => auth.state.me,
  async () => {
    await loadUnread()
  },
  { immediate: true }
)

function submitSearch() {
  const q = searchText.value.trim()
  router.push({ name: 'search', query: q ? { q } : {} })
  suggestOpen.value = false
}

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
  if (Array.isArray(matches)) {
    for (const m of matches) {
      const s = Number(m?.start)
      const l = Number(m?.length)
      if (Number.isFinite(s) && Number.isFinite(l) && l > 0) ranges.push([s, s + l])
    }
  }
  if (ranges.length === 0) return escapeHtml(raw)
  ranges.sort((a, b) => a[0] - b[0])
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

function suggestionTitleHtml(item) {
  const mp = item?._matchesPosition
  return renderWithMatches(item?.title || '', mp?.title)
}

async function loadSuggestions() {
  const q = searchText.value.trim()
  if (!q) {
    suggestions.value = []
    suggestOpen.value = false
    return
  }
  suggestLoading.value = true
  try {
    const { data } = await api.get('/api/posts/suggest/', { params: { q } })
    suggestions.value = Array.isArray(data?.hits) ? data.hits : []
    suggestOpen.value = true
  } catch {
    suggestions.value = []
    suggestOpen.value = false
  } finally {
    suggestLoading.value = false
  }
}

watch(
  () => searchText.value,
  () => {
    if (suggestTimer) clearTimeout(suggestTimer)
    suggestTimer = setTimeout(loadSuggestions, 200)
  }
)

function chooseSuggestion(item) {
  if (!item) return
  // Minimal UX: go to the post directly.
  if (item.id) {
    router.push(`/posts/${item.id}`)
  } else {
    submitSearch()
  }
  suggestOpen.value = false
}

function onFocus() {
  if (suggestions.value.length > 0) suggestOpen.value = true
}

function onBlur() {
  // Delay so click can register.
  setTimeout(() => {
    suggestOpen.value = false
  }, 150)
}

async function openAvatarModal({ reason = '' } = {}) {
  if (!auth.isAuthed()) return
  avatarOpen.value = true
  avatarError.value = ''
  avatarFile.value = null
  avatarPreviewUrl.value = ''

  avatarLoading.value = true
  try {
    const { data } = await api.get('/api/me/avatar/')
    avatarInfo.value = data
  } catch (e) {
    avatarInfo.value = null
    avatarError.value = e?.response?.data?.detail || '加载头像信息失败。'
  } finally {
    avatarLoading.value = false
  }

  // 备注：首次注册后的提醒仅弹一次。
  if (reason === 'post-register') {
    localStorage.removeItem('plc_avatar_prompt')
  }
}

function closeAvatarModal() {
  avatarOpen.value = false
  avatarError.value = ''
  avatarFile.value = null
  if (avatarPreviewUrl.value) {
    try {
      URL.revokeObjectURL(avatarPreviewUrl.value)
    } catch {
      // ignore
    }
  }
  avatarPreviewUrl.value = ''
}

function onChooseAvatarFile(e) {
  const file = e?.target?.files?.[0]
  if (!file) return
  avatarFile.value = file
  if (avatarPreviewUrl.value) {
    try {
      URL.revokeObjectURL(avatarPreviewUrl.value)
    } catch {
      // ignore
    }
  }
  avatarPreviewUrl.value = URL.createObjectURL(file)
}

async function submitAvatar() {
  if (!avatarFile.value) {
    avatarError.value = '请选择头像文件。'
    return
  }

  avatarLoading.value = true
  avatarError.value = ''
  try {
    const fd = new FormData()
    fd.append('avatar', avatarFile.value)
    const { data } = await api.post('/api/me/avatar/', fd)
    avatarInfo.value = data
    await auth.loadMe()
    closeAvatarModal()
  } catch (e) {
    const msg = e?.response?.data?.detail
    const fieldMsg = Array.isArray(e?.response?.data?.avatar) ? e.response.data.avatar.join('；') : ''
    avatarError.value = msg || fieldMsg || '保存头像失败。'
  } finally {
    avatarLoading.value = false
  }
}

watch(
  () => auth.state.me,
  (me) => {
    if (!me) return
    const shouldPrompt = localStorage.getItem('plc_avatar_prompt') === '1'
    if (!shouldPrompt) return
    // 仅在用户还没有头像时提醒。
    if (me.avatar_url) {
      localStorage.removeItem('plc_avatar_prompt')
      return
    }
    openAvatarModal({ reason: 'post-register' })
  }
)
</script>

<template>
  <header class="header">
    <div class="container header-inner topbar">
      <div class="topbar-left">
        <RouterLink to="/" class="brand">Perfect Life CLUB</RouterLink>
      </div>

      <form class="topbar-search" @submit.prevent="submitSearch" role="search">
        <div style="position: relative; width: 100%">
          <input
            v-model="searchText"
            placeholder="搜索"
            aria-label="搜索"
            @focus="onFocus"
            @blur="onBlur"
          />

          <div
            v-if="suggestOpen && (suggestLoading || suggestions.length > 0)"
            class="card"
            style="position: absolute; top: 44px; left: 0; right: 0; z-index: 10"
          >
            <div v-if="suggestLoading" class="muted" style="font-size: 12px">加载中…</div>
            <div v-else class="stack" style="gap: 6px">
              <button
                v-for="s in suggestions"
                :key="s.id || s.title"
                type="button"
                class="btn"
                style="text-align: left; width: 100%"
                @click="chooseSuggestion(s)"
              >
                <span v-html="suggestionTitleHtml(s)"></span>
                <span class="muted" v-if="s.board_slug" style="font-size: 12px"> · {{ s.board_slug }}</span>
              </button>
            </div>
          </div>
        </div>
      </form>

      <div class="topbar-right">
        <template v-if="auth.state.me">
          <button type="button" class="avatar-btn" @click="openAvatarModal()" aria-label="个人中心">
            <img v-if="meAvatarUrl" class="avatar-img" :src="meAvatarUrl" alt="avatar" />
            <span v-else class="avatar-fallback">{{ meInitial }}</span>
          </button>
          <RouterLink to="/notifications" class="btn">
            通知<span v-if="unread > 0">（{{ unread }}）</span>
          </RouterLink>
          <RouterLink to="/posts/new" class="btn btn-solid">发帖</RouterLink>
          <RouterLink v-if="auth.state.me?.is_staff" to="/admin" class="btn">管理</RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/login" class="btn">登录</RouterLink>
          <RouterLink to="/register" class="btn btn-primary">注册</RouterLink>
        </template>
      </div>
    </div>

    <div class="header-subnav">
      <div class="container subnav-inner">
        <nav class="subnav" aria-label="板块导航">
          <template v-if="boardsLoading">
            <span class="muted" style="font-size: 12px">加载板块…</span>
          </template>
          <template v-else>
            <div class="subnav-left">
              <RouterLink class="subnav-link subnav-main" to="/">首页</RouterLink>
              <RouterLink class="subnav-link subnav-main" to="/hot">热门</RouterLink>
              <RouterLink class="subnav-link subnav-main" to="/latest">最近更新</RouterLink>

              <RouterLink v-for="b in canonicalBoards" :key="b.id || b.slug" class="subnav-link" :to="`/b/${b.slug}`">
                {{ b.title || b.name }}
              </RouterLink>
            </div>

            <div class="subnav-right">
              <RouterLink class="subnav-link subnav-strong" :to="`/b/${announcementsBoard.slug}`">
                {{ announcementsBoard.title || announcementsBoard.name }}
              </RouterLink>

              <div class="subnav-menu">
                <span class="subnav-link subnav-strong subnav-menu-trigger" tabindex="0">站务</span>
                <div class="subnav-menu-panel card" role="menu" aria-label="站务">
                  <RouterLink class="btn" style="width: 100%; text-align: left" :to="`/b/${feedbackBoard.slug}`" role="menuitem">
                    {{ feedbackBoard.title || feedbackBoard.name }}
                  </RouterLink>
                  <RouterLink class="btn" style="width: 100%; text-align: left" :to="`/b/${siteLogBoard.slug}`" role="menuitem">
                    {{ siteLogBoard.title || siteLogBoard.name }}
                  </RouterLink>
                  <RouterLink class="btn" style="width: 100%; text-align: left" :to="`/b/${blackRoomBoard.slug}`" role="menuitem">
                    {{ blackRoomBoard.title || blackRoomBoard.name }}
                  </RouterLink>
                </div>
              </div>
            </div>
          </template>
        </nav>
      </div>
    </div>

    <!-- Avatar modal (minimal) -->
    <div v-if="avatarOpen" class="modal-backdrop" @click.self="closeAvatarModal">
      <div class="modal card" role="dialog" aria-modal="true" aria-label="设置头像">
        <div class="row" style="justify-content: space-between">
          <div style="font-weight: 800">设置头像</div>
          <button type="button" class="btn" @click="closeAvatarModal">关闭</button>
        </div>

        <div v-if="avatarError" class="card" style="border-color: #fecaca; background: #fff1f2">
          {{ avatarError }}
        </div>

        <div v-if="avatarLoading" class="muted">加载中…</div>

        <div v-else class="stack">
          <div class="row" style="align-items: center">
            <div class="avatar-preview">
              <img
                v-if="avatarPreviewUrl || meAvatarUrl"
                :src="avatarPreviewUrl || meAvatarUrl"
                alt="avatar"
              />
              <div v-else class="avatar-preview-fallback">{{ meInitial }}</div>
            </div>
            <div class="stack" style="gap: 6px">
              <div class="muted" style="font-size: 12px">
                当前积分：{{ avatarInfo?.points ?? auth.state.me?.activity_score ?? 0 }}
                <span v-if="avatarInfo"> · 本次消耗：{{ avatarInfo.change_cost }}</span>
              </div>
              <div class="muted" style="font-size: 12px">
                备注：首次设置头像免费；后续更换会消耗积分（可在后端设置里调整）。
              </div>
            </div>
          </div>

          <label class="stack" style="gap: 6px">
            <div>选择头像图片（JPEG/PNG/WEBP，≤20MB）</div>
            <input type="file" accept="image/*" @change="onChooseAvatarFile" />
          </label>

          <div class="row" style="justify-content: flex-end">
            <button class="btn btn-primary" type="button" :disabled="avatarLoading" @click="submitAvatar">
              {{ avatarLoading ? '保存中…' : '保存头像' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
