<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { auth } from '../auth'

const logs = ref([])
const error = ref('')
const q = ref('')
const includeArchived = ref(false)

const needSecondary = ref(false)
const secondary = ref('')
const secondaryBusy = ref(false)

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
      JSON.stringify(l.metadata || {}),
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
  needSecondary.value = false
  try {
    const params = {}
    const s = q.value.trim()
    if (s) params.q = s
    if (includeArchived.value && auth.state.me?.is_superuser) params.include_archived = 1
    const { data } = await api.get('/api/admin/audit/', { params })
    logs.value = data
  } catch (e) {
    const detail = e?.response?.data?.detail
    if (detail === 'Secondary password required.') {
      needSecondary.value = true
      error.value = '需要二级密码验证。'
    } else {
      error.value = detail || '加载审计日志失败。'
    }
  }
}

async function verifySecondary() {
  secondaryBusy.value = true
  error.value = ''
  try {
    await api.post('/api/me/secondary-password/verify/', { secondary_password: secondary.value })
    secondary.value = ''
    await auth.loadMe()
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '二级密码验证失败。'
  } finally {
    secondaryBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">审核日志</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>
      <div class="row" style="margin-top: 10px">
        <input v-model="q" placeholder="搜索（@用户名 / UID / action / target / ip）" style="max-width: 420px" />
        <label v-if="auth.state.me?.is_superuser" class="row" style="gap: 6px">
          <input type="checkbox" v-model="includeArchived" />
          <span class="muted">包含归档（>30天，需二级密码）</span>
        </label>
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>

    <div v-if="needSecondary" class="card stack" style="border-color: #fecaca; background: #fff1f2">
      <div style="font-weight: 700">需要二级密码</div>
      <div class="muted">验证后才能查看审核日志。</div>
      <div class="row" style="gap: 10px">
        <input v-model="secondary" type="password" placeholder="输入二级密码" style="max-width: 260px" />
        <button class="btn" :disabled="secondaryBusy" @click="verifySecondary">验证</button>
      </div>
      <div v-if="error" class="muted">{{ error }}</div>
    </div>

    <div v-else-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

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

            <div v-if="l.action === 'user.username.update' && l.metadata && (l.metadata.username_before || l.metadata.username_after)" class="muted">
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
