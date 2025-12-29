<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()
const router = useRouter()

const posts = ref([])
const loading = ref(false)
const keyword = ref((route.query.q || '').toString())

const boards = ref([])

// 筛选状态
const filters = ref({
  ordering: '',
  board: '',
})

const sortOptions = [
  { label: '综合排序', value: '' },
  { label: '最新发布', value: '-created_at' },
  { label: '最多播放', value: '-views_count' },
  { label: '最多点赞', value: '-likes_count' },
]

async function loadBoards() {
  try {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
    boards.value = unwrapList(data)
  } catch {
    boards.value = []
  }
}

function buildQuery() {
  const q = String(keyword.value || '').trim()
  const ordering = String(filters.value.ordering || '').trim()
  const board = String(filters.value.board || '').trim()
  const query = {}
  if (q) query.q = q
  if (ordering) query.ordering = ordering
  if (board) query.board = board
  return query
}

function onSearchSubmit() {
  router.push({ path: '/search', query: buildQuery() })
}

function changeSort(val) {
  filters.value.ordering = val
  onSearchSubmit()
}

function changeBoard(val) {
  filters.value.board = val
  onSearchSubmit()
}

async function doSearch() {
  const q = String(keyword.value || '').trim()
  const ordering = String(filters.value.ordering || '').trim()
  const board = String(filters.value.board || '').trim()

  // 没关键词也没分区时，不请求。
  if (!q && !board) {
    posts.value = []
    return
  }

  loading.value = true
  try {
    const params = {
      search: q || undefined,
      ordering: ordering || undefined,
      board: board || undefined,
    }
    const { data } = await apiGet('/api/posts/', { params, __skipAuth: true })
    posts.value = unwrapList(data)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query,
  (newQuery) => {
    keyword.value = (newQuery.q || '').toString()
    filters.value.ordering = (newQuery.ordering || '').toString()
    filters.value.board = (newQuery.board || '').toString()
    doSearch()
  },
  { immediate: true }
)

onMounted(loadBoards)
</script>

<template>
  <div class="search-page">
    <div class="search-header">
      <div class="search-input-wrap">
        <input v-model="keyword" @keyup.enter="onSearchSubmit" type="text" placeholder="请输入关键词搜索..." />
        <button class="btn-search" type="button" @click="onSearchSubmit">搜索</button>
      </div>
    </div>

    <div class="filter-bar">
      <ul class="filter-tabs">
        <li
          v-for="opt in sortOptions"
          :key="opt.value"
          :class="{ active: filters.ordering === opt.value }"
          @click="changeSort(opt.value)"
        >
          {{ opt.label }}
        </li>
      </ul>

      <div class="filter-extra">
        <select class="board-select" :value="filters.board" @change="changeBoard($event.target.value)">
          <option value="">全部分区</option>
          <option v-for="b in boards" :key="b.id" :value="String(b.id)">{{ b.title }}</option>
        </select>
      </div>
    </div>

    <div class="search-body">
      <div v-if="loading" class="state-text">搜索中...</div>

      <div v-else-if="posts.length > 0" class="bili-grid">
        <PostPreviewCard v-for="p in posts" :key="p.id" :post="p" />
      </div>

      <div v-else class="state-text empty">
        <p>没有找到相关内容</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-page {
  min-height: 100vh;
  background: #fff;
}

/* 顶部搜索区 */
.search-header {
  background: #f1f2f3;
  padding: 30px 0;
  display: flex;
  justify-content: center;
}

.search-input-wrap {
  display: flex;
  width: 600px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e3e5e7;
  overflow: hidden;
  transition: border-color 0.2s;
}

.search-input-wrap:focus-within {
  border-color: #00aeec;
}

.search-input-wrap input {
  flex: 1;
  border: none;
  padding: 12px 16px;
  font-size: 16px;
  outline: none;
}

.btn-search {
  width: 100px;
  background: #00aeec;
  color: #fff;
  border: none;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.btn-search:hover {
  background: #009cd6;
}

/* 筛选条 */
.filter-bar {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
  border-bottom: 1px solid #e3e5e7;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.filter-tabs {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-tabs li {
  font-size: 14px;
  color: #61666d;
  cursor: pointer;
  padding: 4px 0;
  position: relative;
}

.filter-tabs li.active {
  color: #00aeec;
  font-weight: 600;
}

.filter-tabs li.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  height: 2px;
  background: #00aeec;
}

.filter-tabs li:hover {
  color: #00aeec;
}

.board-select {
  height: 34px;
  border: 1px solid #e3e5e7;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #18191c;
}

/* 结果列表 */
.search-body {
  max-width: 1100px;
  margin: 20px auto;
  padding: 0 20px;
}

.state-text {
  text-align: center;
  padding: 60px;
  color: #999;
}

.bili-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

@media (max-width: 980px) {
  .search-input-wrap {
    width: calc(100% - 40px);
  }

  .bili-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .filter-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .bili-grid {
    grid-template-columns: 1fr;
  }
}
</style>
