<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { fmtDateTime } from '../datetime'

const users = ref([])
const error = ref('')
const q = ref('')
const busy = ref({})
const banDays = ref({})
const banReason = ref({})
const muteDays = ref({})
const muteReason = ref({})

const permsOpenUserId = ref(null)
const permsBusy = ref(false)
const permsError = ref('')
const perms = ref({ staff_board_scoped: false, permissions: [] })

const filteredUsers = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return users.value
  return users.value.filter((u) => userHaystack(u).includes(s))
})

function userHaystack(u) {
  return [u?.nickname, u?.username, u?.pid, u?.id]
    .map((x) => String(x || '').toLowerCase())
    .join(' ')
}

async function load() {
  error.value = ''
  try {
    const { data } = await api.get('/api/admin/users/')
    users.value = data
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = detail || '加载用户失败。'
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
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
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
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function mute(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    const daysRaw = muteDays.value[userId]
    const reason = (muteReason.value[userId] || '').trim()
    const payload = { reason }
    if (daysRaw !== undefined && String(daysRaw).trim() !== '') payload.days = Number(daysRaw)
    await api.post(`/api/admin/users/${userId}/mute/`, payload)
    muteDays.value[userId] = ''
    muteReason.value[userId] = ''
    await load()
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function unmute(userId) {
  busy.value[userId] = true
  error.value = ''
  try {
    await api.post(`/api/admin/users/${userId}/unmute/`)
    await load()
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
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
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
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
    const detail = e?.response?.data?.detail
    error.value = detail || '操作失败。'
  } finally {
    busy.value[userId] = false
  }
}

async function toggleBoardPerms(u) {
  permsError.value = ''
  if (permsOpenUserId.value === u.id) {
    permsOpenUserId.value = null
    return
  }
  permsOpenUserId.value = u.id
  permsBusy.value = true
  try {
    const { data } = await api.get(`/api/admin/users/${u.id}/board-perms/`)
    perms.value = {
      staff_board_scoped: !!data?.staff_board_scoped,
      permissions: Array.isArray(data?.permissions) ? data.permissions : [],
    }
    perms.value.permissions.sort((a, b) => String(a?.title || '').localeCompare(String(b?.title || '')))
  } catch (e) {
    const detail = e?.response?.data?.detail
    permsError.value = detail || '加载板块权限失败。'
  } finally {
    permsBusy.value = false
  }
}

async function saveBoardPerms() {
  const userId = permsOpenUserId.value
  if (!userId) return
  permsBusy.value = true
  permsError.value = ''
  try {
    const payload = {
      staff_board_scoped: !!perms.value.staff_board_scoped,
      permissions: (perms.value.permissions || []).map((p) => ({
        board_id: p.board_id,
        can_moderate: !!p.can_moderate,
        can_delete: !!p.can_delete,
      })),
    }
    await api.put(`/api/admin/users/${userId}/board-perms/`, payload)
    await load()
  } catch (e) {
    const detail = e?.response?.data?.detail
    permsError.value = detail || '保存失败。'
  } finally {
    permsBusy.value = false
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
            <div style="font-weight: 700">
              {{ u.nickname || u.username }}
              <span v-if="u.nickname && u.username" class="muted"> · {{ u.username }}</span>
              <span v-if="u.pid" class="muted"> · PID {{ u.pid }}</span>
              <span class="muted"> · #{{ u.id }}</span>
            </div>
            <div class="muted">Lv{{ u.level }} · 活跃度 {{ u.activity_score }} · 限额 {{ u.daily_download_limit }}/天</div>
            <div class="muted" style="margin-top: 4px">
              权限：
              <span v-if="u.is_superuser">超级管理员</span>
              <span v-else-if="u.is_staff">管理员</span>
              <span v-else>普通用户</span>
            </div>
            <div class="muted" v-if="u.is_banned">
              已封禁：{{ u.ban_reason || '未填原因' }}
              <span v-if="u.banned_until"> · 至 {{ fmtDateTime(u.banned_until) }}</span>
              <span v-else> · 永久</span>
            </div>
            <div class="muted" v-if="u.is_muted">
              已禁言：{{ u.mute_reason || '未填原因' }}
              <span v-if="u.muted_until"> · 至 {{ fmtDateTime(u.muted_until) }}</span>
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

              <button
                v-if="u.is_staff && !u.is_superuser"
                class="btn"
                :disabled="permsBusy"
                @click="toggleBoardPerms(u)"
              >
                板块权限
              </button>
            </template>

            <button v-if="!u.is_muted" class="btn" :disabled="busy[u.id]" @click="mute(u.id)">禁言</button>
            <button v-else class="btn" :disabled="busy[u.id]" @click="unmute(u.id)">解除禁言</button>

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

        <div v-if="!u.is_muted" class="row" style="gap: 10px">
          <input
            v-model="muteDays[u.id]"
            placeholder="禁言天数（留空=永久）"
            inputmode="numeric"
            style="max-width: 180px"
          />
          <input v-model="muteReason[u.id]" placeholder="原因（可选）" maxlength="200" />
        </div>

        <div v-if="auth.state.me?.is_superuser && u.is_staff && !u.is_superuser && permsOpenUserId === u.id" class="card stack">
          <div class="row" style="justify-content: space-between">
            <div style="font-weight: 700">分板块权限</div>
            <button class="btn" :disabled="permsBusy" @click="saveBoardPerms">保存</button>
          </div>

          <div v-if="permsError" class="muted">{{ permsError }}</div>

          <label class="row" style="gap: 8px">
            <input type="checkbox" v-model="perms.staff_board_scoped" />
            <span class="muted">启用后该管理员的审核/删除会按板块授权收敛</span>
          </label>

          <div class="muted" v-if="perms.permissions.length === 0">暂无板块</div>

          <div v-for="p in perms.permissions" :key="p.board_id" class="row" style="justify-content: space-between; gap: 10px">
            <div>
              <div style="font-weight: 600">{{ p.title || p.slug || ('#' + p.board_id) }}</div>
              <div class="muted" v-if="p.slug">{{ p.slug }}</div>
            </div>
            <div class="row" style="gap: 12px; flex-wrap: wrap">
              <label class="row" style="gap: 6px">
                <input type="checkbox" v-model="p.can_moderate" />
                <span class="muted">审核</span>
              </label>
              <label class="row" style="gap: 6px">
                <input type="checkbox" v-model="p.can_delete" />
                <span class="muted">删除</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div v-if="filteredUsers.length === 0" class="muted">暂无匹配用户</div>
    </div>
  </div>
</template>
