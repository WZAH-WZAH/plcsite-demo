<script setup>
// Home page ("/")
// Layout goals (based on your reference screenshots):
// 1) Mid-top recommendation area: left 1 large card + right several small cards.
// 2) Below: one horizontal "recommended row" per board, with "查看更多" on the right.
//
// Notes for maintainers:
// - We keep UX minimal and reuse existing primitives: .card/.row/.stack/.btn.
// - Data fetching is intentionally simple. If board count becomes large, add a
//   backend aggregation endpoint (e.g. /api/home) to avoid N+1 requests.

import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiGet, unwrapList } from '../api'

const loading = ref(false)
const error = ref('')

// Top recommendations (hero)
const heroCarouselRaw = ref([]) // admin-configured slides
const heroRightRaw = ref([]) // recommendation tiles

const HERO_CAROUSEL_COUNT = 4
const HERO_RIGHT_COUNT = 6

// Board list + per-board recommended posts
const boards = ref([])
const boardRows = ref([]) // [{ board, posts }]

const heroCarouselPosts = computed(() => (heroCarouselRaw.value || []).slice(0, HERO_CAROUSEL_COUNT))
const heroRightPosts = computed(() => (heroRightRaw.value || []).slice(0, HERO_RIGHT_COUNT))

const heroIndex = ref(0)
const heroCurrent = computed(() => heroCarouselPosts.value?.[heroIndex.value] || null)
const heroHref = computed(() => {
  const url = heroCurrent.value?.link_url
  return (url || '').toString().trim()
})
const heroIsLink = computed(() => Boolean(heroHref.value))
const heroLinkAttrs = computed(() =>
  heroIsLink.value
    ? { href: heroHref.value, target: '_blank', rel: 'noopener noreferrer' }
    : {}
)
let heroTimer = null

function heroNext() {
  const n = heroCarouselPosts.value.length
  if (n <= 1) return
  heroIndex.value = (heroIndex.value + 1) % n
}

function heroPrev() {
  const n = heroCarouselPosts.value.length
  if (n <= 1) return
  heroIndex.value = (heroIndex.value - 1 + n) % n
}

function heroGo(i) {
  const n = heroCarouselPosts.value.length
  if (n <= 1) return
  const idx = Number(i)
  if (!Number.isFinite(idx)) return
  heroIndex.value = Math.max(0, Math.min(idx, n - 1))
}

function startHeroTimer() {
  stopHeroTimer()
  if (heroCarouselPosts.value.length <= 1) return
  heroTimer = setInterval(heroNext, 5000)
}

function stopHeroTimer() {
  if (heroTimer) {
    clearInterval(heroTimer)
    heroTimer = null
  }
}

function fmtTime(s) {
  try {
    return new Date(s).toLocaleString()
  } catch {
    return ''
  }
}

function shortText(s, n = 60) {
  const t = (s || '').toString().replaceAll('\n', ' ').trim()
  if (!t) return ''
  return t.length > n ? t.slice(0, n) + '…' : t
}

// Small concurrency limiter to avoid sending dozens of HTTP requests at once.
// This prevents slow starts when boards become many.
async function mapLimit(items, limit, mapper) {
  const out = []
  const queue = [...items]
  const workers = Array.from({ length: Math.max(1, limit) }, async () => {
    while (queue.length) {
      const item = queue.shift()
      out.push(await mapper(item))
    }
  })
  await Promise.all(workers)
  return out
}

async function loadHero() {
  // Carousel: admin-configured (does NOT use recommendation flow).
  // Right tiles: recommendation (hot -> latest fallback), excluding carousel posts.
  heroCarouselRaw.value = []
  heroRightRaw.value = []

  try {
    const { data } = await apiGet('/api/home/hero/', { __skipAuth: true }, 8000)
    const slides = unwrapList(data)
    heroCarouselRaw.value = slides
  } catch {
    heroCarouselRaw.value = []
  }
  try {
    const { data } = await apiGet('/api/posts/feed/hot/', { __skipAuth: true, params: { days: 7 } }, 8000)
    const list = unwrapList(data)
    heroRightRaw.value = list.slice(0, HERO_RIGHT_COUNT)
    if (heroRightRaw.value.length >= HERO_RIGHT_COUNT) return
  } catch {
    // ignore; fallback below
  }

  try {
    const { data } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true }, 8000)
    const list = unwrapList(data)
    heroRightRaw.value = list.slice(0, HERO_RIGHT_COUNT)
  } catch {
    heroRightRaw.value = []
  }
}

async function loadBoardsAndRows() {
  const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 6000)
  boards.value = unwrapList(data)

  // Per-board recommendation row.
  // We currently reuse existing list API: /api/posts/?board=<id>.
  // Later optimization: backend endpoint returning {board, posts[]} in one call.
  const rows = await mapLimit(boards.value, 6, async (b) => {
    try {
      const { data: postsData } = await apiGet('/api/posts/', { __skipAuth: true, params: { board: b.id } }, 8000)
      const posts = unwrapList(postsData).slice(0, 6)
      return { board: b, posts }
    } catch {
      return { board: b, posts: [] }
    }
  })

  // Keep stable ordering (same as boards list).
  const map = new Map(rows.map((r) => [r.board?.id, r]))
  boardRows.value = boards.value.map((b) => map.get(b.id) || { board: b, posts: [] })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadHero(), loadBoardsAndRows()])
  } catch (e) {
    error.value = '首页加载失败：请确认后端(8000)已启动；开发环境还需启动前端(5173)并确保 /api 代理指向 8000。'
  } finally {
    loading.value = false
  }
}

onMounted(load)

watch(
  () => heroCarouselPosts.value.length,
  () => {
    if (heroIndex.value >= heroCarouselPosts.value.length) heroIndex.value = 0
    startHeroTimer()
  }
)

onMounted(() => {
  startHeroTimer()
})

onUnmounted(() => {
  stopHeroTimer()
})
</script>

<template>
  <div class="stack">
    <div class="home-head">
      <div>
        <h2 class="home-title">首页推荐</h2>
        <div class="muted">上方推荐 + 下方按板块推荐流</div>
      </div>
      <RouterLink class="btn" to="/boards">全部板块</RouterLink>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>
    <div v-if="loading" class="muted" style="padding: 8px 0">加载中…</div>

    <!-- Top recommendations: left carousel + right 6 tiles (left1 right6) -->
    <div v-if="!loading" class="home-hero">
      <component
        v-if="heroCurrent"
        :is="heroIsLink ? 'a' : 'div'"
        class="home-hero-main"
        v-bind="heroLinkAttrs"
        @mouseenter="stopHeroTimer"
        @mouseleave="startHeroTimer"
      >
        <img v-if="heroCurrent.image_url" :src="heroCurrent.image_url" alt="cover" />
        <div class="home-hero-gradient"></div>
        <div class="home-hero-meta">
          <div class="home-hero-main-title">{{ heroCurrent.title || '查看详情' }}</div>
          <div v-if="heroCurrent.description" class="muted" style="font-size: 12px">{{ heroCurrent.description }}</div>
        </div>

        <div v-if="heroCarouselPosts.length > 1" class="home-hero-controls" @click.prevent.stop>
          <button type="button" class="home-hero-arrow" @click.prevent.stop="heroPrev" aria-label="上一张">‹</button>
          <button type="button" class="home-hero-arrow" @click.prevent.stop="heroNext" aria-label="下一张">›</button>
        </div>

        <div v-if="heroCarouselPosts.length > 1" class="home-hero-dots" @click.prevent.stop>
          <button
            v-for="(p, i) in heroCarouselPosts"
            :key="p.id"
            type="button"
            :class="['home-hero-dot', i === heroIndex ? 'is-active' : '']"
            @click.prevent.stop="heroGo(i)"
            :aria-label="`第 ${i + 1} 张`"
          ></button>
        </div>
      </component>

      <div v-else class="card muted" style="display: flex; align-items: center; justify-content: center">
        暂无推荐
      </div>

      <div class="home-hero-grid">
        <RouterLink v-for="p in heroRightPosts" :key="p.id" class="home-hero-tile" :to="`/posts/${p.id}`">
          <img v-if="p.cover_image_url" :src="p.cover_image_url" alt="cover" />
          <div class="home-hero-tile-title">{{ p.title }}</div>
          <div class="muted" style="font-size: 12px">{{ p.author_username }}</div>
        </RouterLink>
      </div>
    </div>

    <!-- Board recommendation rows (lighter sections) -->
    <section v-for="row in boardRows" :key="row.board?.id" class="home-board">
      <div class="row" style="justify-content: space-between">
        <div>
          <div style="font-weight: 800">{{ row.board?.title }}</div>
          <div class="muted" style="font-size: 12px" v-if="row.board?.description">{{ row.board.description }}</div>
        </div>
        <RouterLink class="home-more" :to="`/b/${row.board.slug}`">查看更多</RouterLink>
      </div>

      <div v-if="row.posts?.length" style="margin-top: 10px">
        <div class="home-row-grid">
          <RouterLink v-for="p in row.posts" :key="p.id" class="card" style="padding: 10px; display: grid; gap: 8px" :to="`/posts/${p.id}`">
            <img v-if="p.cover_image_url" :src="p.cover_image_url" alt="cover" style="width: 100%; height: 92px; object-fit: cover; border-radius: 10px" />
            <div style="font-weight: 700">{{ p.title }}</div>
            <div class="muted" style="font-size: 12px">by {{ p.author_username }}</div>
          </RouterLink>
        </div>
      </div>
      <div v-else class="muted" style="margin-top: 10px">该板块暂无可展示内容。</div>
    </section>
  </div>
</template>
