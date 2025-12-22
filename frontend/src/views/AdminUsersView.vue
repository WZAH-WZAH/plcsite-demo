<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { auth } from '../auth'

const users = ref([])
const error = ref('')
const q = ref('')
const busy = ref({})
const banDays = ref({})
const banReason = ref({})

const filteredUsers = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return users.value
  return users.value.filter((u) => String(u.username || '').toLowerCase().includes(s) || String(u.id) === s)
})

async function load() {
  error.value = ''
  try {
    const { data } = await api.get('/api/admin/users/')
    users.value = data
  } catch (e) {
    error.value = '加载用户失败。'
  }
}

async function ban(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    const daysRaw = banDays.value[userId]
    const reason = (banReason.value[userId] || '').trim()
    const payload = { reason }
    if (daysRaw !== undefined && String(daysRaw).trim() !== '') payload.days = Number(daysRaw)
    await api.post(`/api/admin/users/${userId}/ban/`, payload)
    banDays.value[userId] = ''
    banReason.value[userId] = ''
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function unban(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    await api.post(`/api/admin/users/${userId}/unban/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function grantStaff(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    await api.post(`/api/admin/users/${userId}/grant-staff/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function revokeStaff(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    await api.post(`/api/admin/users/${userId}/revoke-staff/`)
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">用户封禁</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>
      <div class="row" style="margin-top: 10px">
        <input v-model="q" placeholder="搜索用户名或ID" style="max-width: 360px" />
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="card stack">
      <div v-for="u in filteredUsers" :key="u.id" class="card stack" style="gap: 10px">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-weight: 700">{{ u.username }} <span class="muted">#{{ u.id }}</span></div>
            <div class="muted">Lv{{ u.level }} · 活跃度 {{ u.activity_score }} · 限额 {{ u.daily_download_limit }}/天</div>
            <div class="muted" style="margin-top: 4px">
              权限：
              <span v-if="u.is_superuser">超级管理员</span>
              <span v-else-if="u.is_staff">管理员</span>
              <span v-else>普通用户</span>
            </div>
            <div class="muted" v-if="u.is_banned">
              已封禁：{{ u.ban_reason || '未填原因' }}
              <span v-if="u.banned_until"> · 至 {{ new Date(u.banned_until).toLocaleString() }}</span>
              <span v-else> · 永久</span>
            </div>
          </div>
          <div class="row">
            <template v-if="auth.state.me?.is_superuser">
              <button
                v-if="!u.is_staff"
                class="btn"
                :disabled="busy[u.id]"
                @click="grantStaff(u.id)"
              >
                设为管理员
              </button>
              <button
                v-else-if="u.is_staff && !u.is_superuser"
                class="btn"
                :disabled="busy[u.id]"
                @click="revokeStaff(u.id)"
              >
                取消管理员
              </button>
            </template>

            <button v-if="!u.is_banned" class="btn" :disabled="busy[u.id]" @click="ban(u.id)">封禁</button>
            <button v-else class="btn" :disabled="busy[u.id]" @click="unban(u.id)">解封</button>
          </div>
        </div>

        <div v-if="!u.is_banned" class="row" style="gap: 10px">
          <input
            v-model="banDays[u.id]"
            placeholder="封禁天数（留空=永久）"
            inputmode="numeric"
            style="max-width: 180px"
          />
          <input v-model="banReason[u.id]" placeholder="原因（可选）" maxlength="200" />
        </div>
      </div>

      <div v-if="filteredUsers.length === 0" class="muted">暂无匹配用户</div>
    </div>
  </div>
</template>
