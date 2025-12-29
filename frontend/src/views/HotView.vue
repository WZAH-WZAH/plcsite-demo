<script setup>
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink } from 'vue-router'
  import { apiGet, unwrapList } from '../api'
  
  const loading = ref(false)
  const error = ref('')
  const boards = ref([])
  
  const boardSlugs = ['games', 'mmd', 'irl', 'tech', 'daily']
  
  const boardBySlug = computed(() => {
    const m = new Map()
    for (const b of boards.value || []) {
      if (b?.slug) m.set(b.slug, b)
    }
    return m
  })
  
  const weekOffset = ref(0)
  const monthOffset = ref(0)
  
  const weekOptions = [
    { value: 0, label: '本周' },
    { value: 1, label: '上周' },
    { value: 2, label: '上上周' },
  ]
  const monthOptions = [
    { value: 0, label: '本月' },
    { value: 1, label: '上月' },
    { value: 2, label: '上上月' },
  ]
  
  function isoEndForOffset(days) {
    const d = new Date(Date.now() - Math.max(0, Number(days) || 0) * 24 * 60 * 60 * 1000)
    return d.toISOString()
  }
  
  function makeRankingState(slugs) {
    const week = {}
    const month = {}
    const prevWeekIds = {}
    const prevMonthIds = {}
    for (const slug of slugs) {
      week[slug] = []
      month[slug] = []
      prevWeekIds[slug] = new Set()
      prevMonthIds[slug] = new Set()
    }
    return { week, month, prevWeekIds, prevMonthIds }
  }
  
  const ranking = ref(makeRankingState(boardSlugs))
  
  function boardTitle(slug) {
    return boardBySlug.value.get(slug)?.title || slug
  }
  
  async function loadBoards() {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
    boards.value = unwrapList(data)
  }
  
  async function loadRank(range, slug) {
    const end = range === 'month' ? isoEndForOffset(monthOffset.value * 30) : isoEndForOffset(weekOffset.value * 7)
    const { data } = await apiGet(
      '/api/posts/rankings/',
      { __skipAuth: true, params: { range, board_slug: slug, limit: 10, end } },
      8000
    )
    return unwrapList(data)
  }
  
  async function loadPrevRankIds(range, slug) {
    const end = range === 'month' ? isoEndForOffset((monthOffset.value + 1) * 30) : isoEndForOffset((weekOffset.value + 1) * 7)
    const { data } = await apiGet(
      '/api/posts/rankings/',
      { __skipAuth: true, params: { range, board_slug: slug, limit: 50, end } },
      8000
    )
    const items = unwrapList(data)
    return new Set(items.map((p) => p?.id).filter((x) => x != null))
  }
  
  async function load() {
    loading.value = true
    error.value = ''
    try {
      await loadBoards()
  
      const tasks = []
      for (const slug of boardSlugs) {
        tasks.push(
          loadRank('week', slug).then((items) => {
            ranking.value.week[slug] = items
          })
        )
        tasks.push(
          loadRank('month', slug).then((items) => {
            ranking.value.month[slug] = items
          })
        )
  
        tasks.push(
          loadPrevRankIds('week', slug).then((ids) => {
            ranking.value.prevWeekIds[slug] = ids
          })
        )
        tasks.push(
          loadPrevRankIds('month', slug).then((ids) => {
            ranking.value.prevMonthIds[slug] = ids
          })
        )
      }
      await Promise.all(tasks)
    } catch (e) {
      error.value = '热门榜单加载失败。'
    } finally {
      loading.value = false
    }
  }
  
  function isDominating(range, slug, postId) {
    if (!postId) return false
    if (range === 'month') return ranking.value.prevMonthIds?.[slug]?.has(postId)
    return ranking.value.prevWeekIds?.[slug]?.has(postId)
  }
  
  onMounted(load)
  </script>
  
  <template>
    <div class="stack">
      <div class="home-head">
        <div>
          <h2 class="home-title">热门</h2>
          <div class="muted">按周榜 / 月榜展示各板块 Top10</div>
        </div>
        <RouterLink class="btn" to="/boards">全部板块</RouterLink>
      </div>
  
      <div class="row" style="justify-content: space-between">
        <div class="muted" style="font-size: 12px">支持查看历史榜单</div>
      </div>
  
      <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>
      <div v-if="loading" class="muted">加载中…</div>
  
      <template v-else>
        <section class="stack" style="gap: 10px">
          <div class="row" style="justify-content: space-between">
            <div style="font-weight: 800">周榜 Top10</div>
            <label class="row" style="gap: 8px">
              <span class="muted" style="font-size: 12px">周榜</span>
              <select class="btn" v-model.number="weekOffset" @change="load">
                <option v-for="o in weekOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </label>
          </div>
  
          <div class="rank-grid">
            <section v-for="slug in boardSlugs" :key="`week-${slug}`" class="card rank-card">
              <div class="row" style="justify-content: space-between">
                <div style="font-weight: 800">{{ boardTitle(slug) }}</div>
                <RouterLink class="btn" :to="{ name: 'board-posts', params: { slug }, query: { sort: 'hot', range: 'week' } }">查看更多</RouterLink>
              </div>
  
              <ol class="stack" style="gap: 8px; padding-left: 0; margin-top: 10px; list-style: none;">
                <li v-for="(p, idx) in ranking.week[slug]" :key="p.id" class="rank-item">
                  <span :class="['rank-num', idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : idx === 2 ? 'rank-3' : 'rank-normal']">
                    {{ idx + 1 }}
                  </span>
                  
                  <RouterLink :to="`/posts/${p.id}`" class="post-title" :title="p.title">{{ p.title }}</RouterLink>
                  
                  <div class="meta-right">
                      <span v-if="isDominating('week', slug, p.id)" class="badge-dominant">霸榜</span>
                      <span class="hot-score muted">热度 {{ p.hot_score_100 ?? 0 }}</span>
                  </div>
                </li>
                <li v-if="ranking.week[slug]?.length === 0" class="muted" style="padding-left: 8px;">暂无数据</li>
              </ol>
            </section>
          </div>
        </section>
  
        <section class="stack" style="gap: 10px">
          <div class="row" style="justify-content: space-between">
            <div style="font-weight: 800">月榜 Top10</div>
            <label class="row" style="gap: 8px">
              <span class="muted" style="font-size: 12px">月榜</span>
              <select class="btn" v-model.number="monthOffset" @change="load">
                <option v-for="o in monthOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </label>
          </div>
  
          <div class="rank-grid">
            <section v-for="slug in boardSlugs" :key="`month-${slug}`" class="card rank-card">
              <div class="row" style="justify-content: space-between">
                <div style="font-weight: 800">{{ boardTitle(slug) }}</div>
                <RouterLink class="btn" :to="{ name: 'board-posts', params: { slug }, query: { sort: 'hot', range: 'month' } }">查看更多</RouterLink>
              </div>
  
              <ol class="stack" style="gap: 8px; padding-left: 0; margin-top: 10px; list-style: none;">
                <li v-for="(p, idx) in ranking.month[slug]" :key="p.id" class="rank-item">
                  <span :class="['rank-num', idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : idx === 2 ? 'rank-3' : 'rank-normal']">
                    {{ idx + 1 }}
                  </span>
                  
                  <RouterLink :to="`/posts/${p.id}`" class="post-title" :title="p.title">{{ p.title }}</RouterLink>
                  
                  <div class="meta-right">
                      <span v-if="isDominating('month', slug, p.id)" class="badge-dominant">霸榜</span>
                      <span class="hot-score muted">热度 {{ p.hot_score_100 ?? 0 }}</span>
                  </div>
                </li>
                <li v-if="ranking.month[slug]?.length === 0" class="muted" style="padding-left: 8px;">暂无数据</li>
              </ol>
            </section>
          </div>
        </section>
      </template>
    </div>
  </template>
  
  <style scoped>
  .rank-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
  
  .rank-card {
    padding: 14px;
  }
  
  .rank-item {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
    width: 100%;
  }
  
  /* 序号样式 */
  .rank-num {
      display: inline-block;
      width: 24px;
      text-align: center;
      font-size: 13px;
      font-weight: 700;
      flex-shrink: 0;
      font-family: monospace;
      line-height: 1;
  }
  .rank-1 { color: #d97706; font-size: 17px; font-weight: 900; }
  .rank-2 { color: #52525b; font-size: 16px; font-weight: 900; }
  .rank-3 { color: #b45309; font-size: 16px; font-weight: 900; }
  .rank-normal { color: #9ca3af; font-weight: 500; font-size: 12px; }
  
  /* 标题样式：核心修改 */
  .post-title {
      flex: 1;             /* 占据所有剩余空间 */
      width: 0;            /* 必须：允许 flex item 压缩到小于内容宽度 */
      white-space: nowrap; /* 强制不换行 */
      overflow: hidden;    /* 隐藏溢出内容 */
      text-overflow: ellipsis; /* 显示省略号 */
      color: inherit;
      text-decoration: none;
  }
  .post-title:hover {
      text-decoration: underline;
      color: #2563eb;
  }
  
  /* 右侧元数据容器 */
  .meta-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0; /* 防止被挤压 */
      margin-left: auto; /* 确保靠右（双重保险） */
  }
  
  /* 霸榜标签 */
  .badge-dominant {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 800;
    padding: 1px 4px;
    border-radius: 4px;
    border: 1px solid #fecaca;
    background: #fff1f2;
    color: #ef4444;
    white-space: nowrap;
    height: 18px;
  }
  
  /* 热度数值：固定宽度确保对齐 */
  .hot-score {
      width: 65px; /* 给一个固定宽度，容纳 '热度 100' */
      text-align: right;
      font-size: 12px;
      font-variant-numeric: tabular-nums; /* 等宽数字，对齐更整齐 */
  }
  </style>