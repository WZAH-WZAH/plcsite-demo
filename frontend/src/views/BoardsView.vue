<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, unwrapList } from '../api'

const boards = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
    boards.value = unwrapList(data)
  } catch (e) {
    error.value = '加载板块失败。请确认后端已启动。'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <div>
          <h2 style="margin: 0 0 6px">板块</h2>
          <div class="muted">简约舒适 · 多端适配（开发中）</div>
        </div>
        <div class="row">
          <RouterLink class="btn" to="/posts/new">发帖</RouterLink>
          <RouterLink class="btn" to="/me">我的</RouterLink>
        </div>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="stack">
      <div v-if="loading" class="muted">加载中…</div>
      <RouterLink
        v-for="b in boards"
        :key="b.id"
        class="card"
        :to="`/b/${b.slug}`"
      >
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ b.title }}</div>
            <div class="muted" v-if="b.description">{{ b.description }}</div>
          </div>
          <div class="muted">进入</div>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
