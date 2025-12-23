<script setup>
  // Home page ("/")
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
  import { apiGet, unwrapList } from '../api'
  import PostPreviewCard from '../components/PostPreviewCard.vue'
  
  const loading = ref(false)
  const error = ref('')
  
  // --- 数据状态 ---
  const heroCarouselRaw = ref([]) // 轮播图数据
  const heroRightRaw = ref([])    // 推荐网格数据
  
  const HERO_CAROUSEL_COUNT = 5   // 轮播图数量
  const HERO_RIGHT_COUNT = 6      // 右侧网格必须是6个（2行x3列）
  
  // 板块推荐流数据
  const boards = ref([])
  const boardRows = ref([]) 

  const homeExcludedBoardSlugs = new Set(['announcements', 'feedback', 'site-log', 'blackroom'])
  
  // --- 计算属性 ---
  const heroCarouselPosts = computed(() => (heroCarouselRaw.value || []).slice(0, HERO_CAROUSEL_COUNT))
  const heroRightPosts = computed(() => (heroRightRaw.value || []).slice(0, HERO_RIGHT_COUNT))
  
  // 轮播图逻辑
  const heroIndex = ref(0)
  const heroCurrent = computed(() => heroCarouselPosts.value?.[heroIndex.value] || null)
  const heroHref = computed(() => (heroCurrent.value?.link_url || '').toString().trim())
  const heroIsLink = computed(() => Boolean(heroHref.value))
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
    heroIndex.value = Math.max(0, Math.min(Number(i), n - 1))
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
  
  // 简单的并发限制
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
    heroCarouselRaw.value = []
    heroRightRaw.value = []
  
    // 1. 获取轮播图
    try {
      const { data } = await apiGet('/api/home/hero/', { __skipAuth: true }, 5000)
      heroCarouselRaw.value = unwrapList(data)
    } catch {
      heroCarouselRaw.value = []
    }
  
    // 2. 获取右侧推荐
    try {
      const { data } = await apiGet('/api/posts/feed/hot/', { __skipAuth: true, params: { days: 7 } }, 5000)
        const hotList = unwrapList(data)

        // 注意：主页轮播是“运营位”（可能是外链/不绑定帖子），不能拿轮播的 id 去和帖子 id 做去重。
        // 这里采用：热门优先 + 最新补齐，并只在 hot/latest 两个源之间按 post.id 去重。
        const picked = []
        const pickedIds = new Set()

        for (const p of hotList) {
          if (picked.length >= HERO_RIGHT_COUNT) break
          if (p?.id == null) continue
          if (homeExcludedBoardSlugs.has(p?.board_slug)) continue
          if (pickedIds.has(p.id)) continue
          picked.push(p)
          pickedIds.add(p.id)
        }

        if (picked.length < HERO_RIGHT_COUNT) {
          const { data: latestData } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true }, 5000)
          const latestList = unwrapList(latestData)
          for (const p of latestList) {
            if (picked.length >= HERO_RIGHT_COUNT) break
            if (p?.id == null) continue
            if (homeExcludedBoardSlugs.has(p?.board_slug)) continue
            if (pickedIds.has(p.id)) continue
            picked.push(p)
            pickedIds.add(p.id)
          }
        }

        heroRightRaw.value = picked
    } catch {
      heroRightRaw.value = []
    }
  }
  
  async function loadBoardsAndRows() {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 5000)
    boards.value = unwrapList(data).filter((b) => !homeExcludedBoardSlugs.has(b?.slug))
  
    // 获取每个板块的前 6 个帖子
    const rows = await mapLimit(boards.value, 4, async (b) => {
      try {
        const { data: postsData } = await apiGet('/api/posts/', { __skipAuth: true, params: { board: b.id } }, 5000)
        return { board: b, posts: unwrapList(postsData).slice(0, 6) }
      } catch {
        return { board: b, posts: [] }
      }
    })
  
    const map = new Map(rows.map((r) => [r.board?.id, r]))
    boardRows.value = boards.value.map((b) => map.get(b.id) || { board: b, posts: [] })
  }
  
  async function load() {
    loading.value = true
    error.value = ''
    try {
      await Promise.all([loadHero(), loadBoardsAndRows()])
    } catch (e) {
      console.error(e)
      error.value = '首页加载失败，请检查网络或后端状态。'
    } finally {
      loading.value = false
    }
  }
  
  onMounted(load)
  
  watch(() => heroCarouselPosts.value.length, () => {
    if (heroIndex.value >= heroCarouselPosts.value.length) heroIndex.value = 0
    startHeroTimer()
  })
  
  onMounted(startHeroTimer)
  onUnmounted(stopHeroTimer)
  </script>
  
  <template>
    <div class="stack">
      <div class="home-head" style="padding-bottom: 12px;">
        <div class="row" style="gap: 16px; font-size: 14px;">
          <div style="display: flex; align-items: center; gap: 4px; color: #18191c; font-weight: 600; font-size: 20px;">
            <span style="color: #ff6699;">★</span> 热门推荐
          </div>
        </div>
        <RouterLink class="btn" style="padding: 6px 12px; font-size: 13px;" to="/boards">全部板块</RouterLink>
      </div>
  
      <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>
      
      <div v-if="!loading && (heroCurrent || heroRightPosts.length)" class="bili-recommend-box">
        
        <div class="bili-carousel-wrap">
          <component
            :is="heroIsLink ? 'a' : 'div'"
            :href="heroIsLink ? heroHref : undefined"
            :target="heroIsLink ? '_blank' : undefined"
            :rel="heroIsLink ? 'noopener noreferrer' : undefined"
            class="bili-carousel"
            @mouseenter="stopHeroTimer"
            @mouseleave="startHeroTimer"
          >
            <div v-if="heroCurrent" style="width: 100%; height: 100%; position: relative;">
               <img :src="heroCurrent.image_url" class="bili-cover-img" />
               <div class="bili-carousel-mask"></div>
               <div class="bili-carousel-info">
                 <div class="bili-carousel-title">{{ heroCurrent.title }}</div>
               </div>
            </div>
            <div v-else class="empty-placeholder">暂无推荐</div>
  
            <div class="bili-dots" v-if="heroCarouselPosts.length > 1" @click.prevent.stop>
              <span 
                v-for="(p, i) in heroCarouselPosts" 
                :key="p.id"
                :class="['dot', { active: i === heroIndex }]"
                @click.prevent.stop="heroGo(i)"
              ></span>
            </div>
            
            <div class="bili-arrows" v-if="heroCarouselPosts.length > 1" @click.prevent.stop>
               <button @click.prevent.stop="heroPrev">‹</button>
               <button @click.prevent.stop="heroNext">›</button>
            </div>
          </component>
        </div>
  
        <div class="bili-grid">
          <PostPreviewCard v-for="p in heroRightPosts" :key="p.id" :post="p" />
        </div>
      </div>
  
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
            <PostPreviewCard v-for="p in row.posts" :key="p.id" :post="p" />
          </div>
        </div>
        <div v-else class="muted" style="margin-top: 10px">该板块暂无可展示内容。</div>
      </section>
  
    </div>
  </template>
  
  <style scoped>
  /* --- Bilibili 风格样式 --- */
  
  .bili-recommend-box {
    display: flex;
    gap: 12px;
    width: 100%;
    height: 380px; 
    margin-bottom: 20px;
  }
  
  /* 左侧轮播 */
  .bili-carousel-wrap {
    width: 42%; 
    height: 100%;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
  }
  
  .bili-carousel {
    display: block;
    width: 100%;
    height: 100%;
    position: relative;
    cursor: pointer;
    background: #f1f2f3;
  }
  
  .bili-cover-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  
  .bili-carousel-mask {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 50%;
    background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
    pointer-events: none;
  }
  
  .bili-carousel-info {
    position: absolute;
    bottom: 12px;
    left: 12px;
    right: 12px;
    color: #fff;
  }
  
  .bili-carousel-title {
    font-size: 18px;
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
  
  .bili-dots {
    position: absolute;
    bottom: 12px;
    right: 16px;
    display: flex;
    gap: 6px;
    pointer-events: auto; 
  }
  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: rgba(255,255,255,0.4);
    cursor: pointer;
    transition: all 0.2s;
  }
  .dot.active {
    background: #fff;
    transform: scale(1.2);
  }
  
  .bili-arrows button {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 32px; height: 32px;
    border: none;
    background: rgba(0,0,0,0.3);
    color: #fff;
    border-radius: 4px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
  }
  .bili-carousel:hover .bili-arrows button {
    opacity: 1;
  }
  .bili-arrows button:first-child { left: 8px; }
  .bili-arrows button:last-child { right: 8px; }
  
  /* 右侧 Grid */
  .bili-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(2, 1fr);
    gap: 12px;
  }
  
  /* 卡片通用 */
  .bili-card {
    display: flex;
    flex-direction: column;
    text-decoration: none;
    color: inherit;
  }
  
  .bili-card-cover {
    position: relative;
    width: 100%;
    height: 0;
    padding-bottom: 62.5%; /* 16:10 */
    background: #f1f2f3;
    border-radius: 6px;
    overflow: hidden;
  }
  
  .bili-card-cover img {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: cover;
  }
  
  .bili-stats {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    padding: 30px 8px 6px;
    background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
    color: #fff;
    font-size: 11px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .bili-card-info {
    margin-top: 8px;
  }
  
  .bili-title {
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
    color: #18191c;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    transition: color 0.2s;
  }
  .bili-card:hover .bili-title {
    color: #00aeec;
  }
  
  .bili-author {
    font-size: 12px;
    color: #9499a0;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .up-icon {
    border: 1px solid #9499a0;
    border-radius: 3px;
    padding: 0 2px;
    font-size: 10px;
    line-height: 12px;
    transform: scale(0.9);
    margin-right: 2px; /* 微调间距 */
  }
  
  /* 移动端适配 */
  @media (max-width: 900px) {
    .bili-recommend-box {
      flex-direction: column;
      height: auto;
    }
    .bili-carousel-wrap {
      width: 100%;
      height: 0;
      padding-bottom: 56.25%; /* 16:9 */
    }
    .bili-carousel {
      position: absolute; 
      inset: 0;
    }
    .bili-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  </style>