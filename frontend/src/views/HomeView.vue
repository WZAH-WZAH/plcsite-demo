<script setup>
  // Home page ("/")
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
  import { apiGet, unwrapList } from '../api'
  // 引入你现有的组件
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

  // 首页不展示这些板块（后续再考虑在首页其它位置呈现）
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
  
  // 并发加载工具
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
      const list = unwrapList(data)
      // 过滤掉已经在轮播图里的帖子
      const carouselIds = new Set(heroCarouselRaw.value.map(c => c.id))
      heroRightRaw.value = list
        .filter(p => !carouselIds.has(p.id))
        .filter(p => !homeExcludedBoardSlugs.has(p?.board_slug))
        .slice(0, HERO_RIGHT_COUNT)
      
      // 补齐逻辑
      if (heroRightRaw.value.length < HERO_RIGHT_COUNT) {
        const { data: latestData } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true }, 5000)
        const latestList = unwrapList(latestData)
          .filter(p => !carouselIds.has(p.id))
          .filter(p => !homeExcludedBoardSlugs.has(p?.board_slug))
        const existingIds = new Set(heroRightRaw.value.map(p => p.id))
        for (const p of latestList) {
          if (heroRightRaw.value.length >= HERO_RIGHT_COUNT) break
          if (!existingIds.has(p.id)) {
            heroRightRaw.value.push(p)
            existingIds.add(p.id)
          }
        }
      }
    } catch {
      heroRightRaw.value = []
    }
  }
  
  async function loadBoardsAndRows() {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 5000)
    boards.value = unwrapList(data).filter((b) => !homeExcludedBoardSlugs.has(b?.slug))
  
    // 获取每个板块的前 5 个帖子 (为了适配一行5个的布局)
    const rows = await mapLimit(boards.value, 4, async (b) => {
      try {
        const { data: postsData } = await apiGet('/api/posts/', { __skipAuth: true, params: { board: b.id } }, 5000)
        return { board: b, posts: unwrapList(postsData).slice(0, 5) }
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
      
      <div v-if="loading" class="bili-recommend-box" style="background: #f4f5f7; border-radius: 6px; align-items: center; justify-content: center; color: #999;">
         加载推荐内容...
      </div>
  
      <div v-else-if="heroCurrent || heroRightPosts.length" class="bili-recommend-box">
        
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
          <PostPreviewCard 
            v-for="p in heroRightPosts" 
            :key="p.id" 
            :post="p" 
          />
        </div>
      </div>
  
      <section v-for="row in boardRows" :key="row.board?.id" class="home-board">
        <div class="row" style="justify-content: space-between; margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 8px;">
             <div style="width:32px; height:32px; background:#f1f2f3; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#666; font-size: 14px; font-weight: bold;">
               #
             </div>
             <div>
               <div style="font-weight: 600; font-size: 18px; line-height: 1.2;">{{ row.board?.title }}</div>
               <div class="muted" style="font-size: 12px" v-if="row.board?.description">{{ row.board.description }}</div>
             </div>
          </div>
          <RouterLink class="btn btn-sm" :to="`/b/${row.board.slug}`">更多 ›</RouterLink>
        </div>
  
        <div v-if="row.posts?.length">
          <div class="bili-row-grid">
            <PostPreviewCard 
              v-for="p in row.posts" 
              :key="p.id" 
              :post="p" 
            />
          </div>
        </div>
        <div v-else class="muted" style="margin-top: 10px; padding: 20px; text-align: center; background: #f9f9f9; border-radius: 6px;">
          该板块暂无可展示内容。
        </div>
      </section>
  
    </div>
  </template>
  
  <style scoped>
  /* 核心布局样式 
    注意：卡片样式已移至 PostPreviewCard.vue，此处只需管理容器布局
  */
  
  /* 顶部推荐容器 */
  .bili-recommend-box {
    display: flex;
    gap: 12px;
    width: 100%;
    height: 380px; /* 固定高度，确保左右对齐 */
    margin-bottom: 30px;
  }
  
  /* 左侧轮播图容器 */
  .bili-carousel-wrap {
    width: 42%; 
    height: 100%;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
  }
  
  /* 轮播图内部元素 */
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
    bottom: 12px; left: 12px; right: 12px;
    color: #fff;
  }
  .bili-carousel-title {
    font-size: 18px;
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
  
  /* 轮播图圆点 */
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
  
  /* 轮播图箭头 */
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
  
  /* 右侧 6 宫格网格 */
  .bili-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(3, 1fr); /* 3列 */
    grid-template-rows: repeat(2, 1fr);    /* 2行 */
    gap: 12px;
  }
  
  /* 下方板块 单行 Grid (一行5个) */
  .home-board {
    margin-bottom: 30px;
  }
  .bili-row-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr); 
    gap: 12px;
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
      position: absolute; inset: 0;
    }
    .bili-grid {
      grid-template-columns: repeat(2, 1fr); /* 手机端2列 */
    }
    .bili-row-grid {
      grid-template-columns: repeat(2, 1fr); /* 手机端板块内容也变2列 */
    }
  }
  </style>