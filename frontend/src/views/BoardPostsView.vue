<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import { auth } from '../auth'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()

const boards = ref([])
const posts = ref([])
const heroSlides = ref([])
const loading = ref(false)
const error = ref('')

const board = computed(() => boards.value.find((b) => b.slug === route.params.slug))

const RIGHT_TOP_COUNT = 3

const allPosts = computed(() => posts.value || [])
const heroPostIds = computed(() => new Set((heroSlides.value || []).map((s) => s.post_id).filter(Boolean)))
const contentPosts = computed(() => allPosts.value.filter((p) => !heroPostIds.value.has(p.id)))
const rightTopPosts = computed(() => contentPosts.value.slice(0, RIGHT_TOP_COUNT))
const gridPosts = computed(() => contentPosts.value.slice(RIGHT_TOP_COUNT))

const heroIndex = ref(0)
const heroCurrent = computed(() => (heroSlides.value || [])?.[heroIndex.value] || null)
let heroTimer = null

function heroNext() {
  const n = heroSlides.value.length
  if (n <= 1) return
  heroIndex.value = (heroIndex.value + 1) % n
}

function heroPrev() {
  const n = heroSlides.value.length
  if (n <= 1) return
  heroIndex.value = (heroIndex.value - 1 + n) % n
}

function heroGo(i) {
  const n = heroSlides.value.length
  if (n <= 1) return
  const idx = Number(i)
  if (!Number.isFinite(idx)) return
  heroIndex.value = Math.max(0, Math.min(idx, n - 1))
}

function startHeroTimer() {
  stopHeroTimer()
  if (heroSlides.value.length <= 1) return
  heroTimer = setInterval(heroNext, 5000)
}

function stopHeroTimer() {
  if (heroTimer) {
    clearInterval(heroTimer)
    heroTimer = null
  }
}

function statusText(s) {
  if (s === 'published') return '已发布'
  if (s === 'pending') return '待审核'
  if (s === 'rejected') return '已拒绝'
  return s || ''
}

function fmtDate(s) {
  try {
    return new Date(s).toLocaleDateString()
  } catch {
    return ''
  }
}

const heroImageUrl = computed(() => {
  const s = heroCurrent.value
  if (!s) return ''
  return (s.image_url || s.post_cover_image_url || '').toString()
})

const heroTitle = computed(() => {
  const s = heroCurrent.value
  if (!s) return ''
  return (s.title || s.post_title || '').toString()
})

const heroDesc = computed(() => {
  const s = heroCurrent.value
  if (!s) return ''
  return (s.description || '').toString()
})

async function loadBoards() {
  const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
  boards.value = unwrapList(data)
}

async function loadHero() {
  heroSlides.value = []
  heroIndex.value = 0
  try {
    const slug = route.params.slug
    const { data } = await apiGet(`/api/boards/${slug}/hero/`, { __skipAuth: true }, 8000)
    heroSlides.value = unwrapList(data)
  } catch {
    heroSlides.value = []
  }
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
    await Promise.all([loadHero(), loadPosts()])
  } catch (e) {
    error.value = '加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
watch(() => route.params.slug, loadAll)

watch(
  () => heroSlides.value.length,
  () => {
    if (heroIndex.value >= heroSlides.value.length) heroIndex.value = 0
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
        <h2 class="home-title">{{ board?.title || '板块' }}</h2>
        <div class="muted">{{ board?.description || '浏览与发布内容' }}</div>
      </div>
      <div class="row">
        <RouterLink class="btn" to="/">返回</RouterLink>
        <RouterLink class="btn btn-primary" to="/posts/new">发帖</RouterLink>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div v-if="loading" class="muted">加载中…</div>

    <template v-else>
      <!-- Top row: carousel + 3 posts -->
      <div class="home-hero">
        <RouterLink
          v-if="heroCurrent"
          class="home-hero-main"
          :to="`/posts/${heroCurrent.post_id}`"
          @mouseenter="stopHeroTimer"
          @mouseleave="startHeroTimer"
        >
          <img v-if="heroImageUrl" :src="heroImageUrl" alt="cover" />
          <div class="home-hero-gradient"></div>
          <div class="home-hero-meta">
            <div class="home-hero-main-title">{{ heroTitle || '查看详情' }}</div>
            <div v-if="heroDesc" class="muted" style="font-size: 12px">{{ heroDesc }}</div>
            <div class="muted" style="font-size: 12px" v-else>{{ heroCurrent.post_author_username }}</div>
          </div>

          <div v-if="heroSlides.length > 1" class="home-hero-controls" @click.prevent.stop>
            <button type="button" class="home-hero-arrow" @click.prevent.stop="heroPrev" aria-label="上一张">‹</button>
            <button type="button" class="home-hero-arrow" @click.prevent.stop="heroNext" aria-label="下一张">›</button>
          </div>

          <div v-if="heroSlides.length > 1" class="home-hero-dots" @click.prevent.stop>
            <button
              v-for="(p, i) in heroSlides"
              :key="p.id || p.post_id"
              type="button"
              :class="['home-hero-dot', i === heroIndex ? 'is-active' : '']"
              @click.prevent.stop="heroGo(i)"
              :aria-label="`第 ${i + 1} 张`"
            ></button>
          </div>
        </RouterLink>

        <div v-else class="card muted" style="display: flex; align-items: center; justify-content: center">暂无帖子</div>

        <div class="home-hero-grid">
          <PostPreviewCard v-for="p in rightTopPosts" :key="p.id" :post="p" :meta="fmtDate(p.created_at)" />
        </div>
      </div>

      <!-- Grid: 5 per row -->
      <div class="board-grid" v-if="gridPosts.length > 0">
        <PostPreviewCard v-for="p in gridPosts" :key="p.id" :post="p" :meta="fmtDate(p.created_at)" />
      </div>

      <div v-if="posts.length === 0" class="muted">暂无帖子</div>
    </template>
  </div>
</template>
