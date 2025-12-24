<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const logs = ref([])
const error = ref('')
const actor = ref('')
const q = ref('')

const filteredLogs = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return logs.value
  return logs.value.filter((l) => {
    const hay = [
      l.action,
      l.actor_nickname,
      l.actor_username,
      l.actor_pid,
      l.actor_id,
      l.actor,
      l.target_type,
      l.target_id,
      l.ip,
    ]
      .map((x) => String(x || '').toLowerCase())
      .join(' ')
    return hay.includes(s)
  })
})

function fmtMeta(meta) {
  if (meta === null || meta === undefined) return ''
  if (typeof meta === 'string') return meta
  try {
    return JSON.stringify(meta, null, 2)
  } catch {
    return String(meta)
  }
}

async function load() {
  error.value = ''
  try {
    const params = {}
    const a = actor.value.trim()
    if (a) params.actor = a
    const { data } = await api.get('/api/admin/audit/', { params })
    logs.value = data
  } catch (e) {
    error.value = '加载审计日志失败。'
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">审计日志</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>
      <div class="row" style="margin-top: 10px">
        <input v-model="actor" placeholder="按用户名或UID筛选（@xxx 或数字）" style="max-width: 320px" />
        <input v-model="q" placeholder="本页搜索（action / target / ip 等）" style="max-width: 320px" />
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="card stack">
      <div v-for="l in filteredLogs" :key="l.id" class="card">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ l.action }}</div>
            <div class="muted">
              {{ new Date(l.created_at).toLocaleString() }} ·
              actor={{ l.actor_nickname || l.actor_username || l.actor || 'null' }}
              <template v-if="l.actor_nickname && l.actor_username"> · {{ l.actor_username }}</template>
              <template v-if="l.actor_pid"> · PID {{ l.actor_pid }}</template>
              <template v-if="l.actor_id"> · #{{ l.actor_id }}</template>
              · ip={{ l.ip || '-' }}
            </div>

            <div
              v-if="l.action === 'user.username.update' && l.metadata && (l.metadata.username_before || l.metadata.username_after)"
              class="muted"
            >
              用户名：{{ l.metadata.username_before || '-' }} → {{ l.metadata.username_after || '-' }}
            </div>

            <div class="muted" v-if="l.target_type">target={{ l.target_type }}#{{ l.target_id }}</div>
          </div>
          <pre class="muted" style="max-width: 420px; overflow: auto; margin: 0; white-space: pre-wrap">
{{ fmtMeta(l.metadata) }}
          </pre>
        </div>
      </div>
      <div v-if="filteredLogs.length === 0" class="muted">暂无</div>
    </div>
  </div>
</template>
