<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet, unwrapList } from '../api'
import PostPreviewCard from '../components/PostPreviewCard.vue'

const route = useRoute()
const board = ref(null)
const posts = ref([])
const loading = ref(true)

const boardIconUrl = computed(() => board.value?.icon_url || board.value?.icon || '')

async function fetchBoard() {
  loading.value = true
  const slug = route.params.slug
  try {
    const { data: boardData } = await apiGet(`/api/boards/${slug}/`, { __skipAuth: true })
    board.value = boardData

    const { data: postsData } = await apiGet(
      '/api/posts/',
      {
        params: { board: boardData.id },
        __skipAuth: true,
      },
      8000
    )
    posts.value = unwrapList(postsData)
  } catch (e) {
    console.error(e)
    board.value = null
    posts.value = []
  } finally {
    loading.value = false
  }
}

watch(() => route.params.slug, fetchBoard)
onMounted(fetchBoard)
</script>

<template>
  <div class="stack">
    <div class="board-header" v-if="board">
      <div class="board-icon">
        <img v-if="boardIconUrl" :src="boardIconUrl" alt="icon" />
        <span v-else>#</span>
      </div>
      <div class="board-info">
        <h1>{{ board.title }}</h1>
        <p class="desc">{{ board.description || '暂无介绍' }}</p>
      </div>
    </div>

    <div v-if="loading" class="muted" style="margin-top: 20px">加载中...</div>
    <div v-else-if="posts.length" class="bili-grid" style="margin-top: 20px">
      <PostPreviewCard v-for="p in posts" :key="p.id" :post="p" />
    </div>
    <div v-else class="muted" style="margin-top: 20px; text-align: center; padding: 40px">该板块暂无内容</div>
  </div>
</template>

<style scoped>
.board-header {
  display: flex;
  align-items: center;
  gap: 20px;
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e3e5e7;
}
.board-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: #f1f2f3;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-size: 24px;
  color: #999;
}
.board-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.board-info h1 {
  margin: 0 0 8px 0;
  font-size: 22px;
}
.board-info .desc {
  color: #9499a0;
  font-size: 13px;
  margin: 0;
}
</style>
