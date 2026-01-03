<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { auth } from '../auth'

const loading = ref(false)
const error = ref('')

const users = ref([])
const policies = ref([])
const assignments = ref([])

const selectedUserPid = ref('')
const selectedRole = ref('')

const roleBindForm = ref({ role: '', dom: '*' })
const rolePolicyForm = ref({ dom: '*', obj: '', act: '' })

const mePid = computed(() => String(auth.state.me?.pid || ''))

const selectedUserName = computed(() => {
  if (!selectedUser.value) return ''
  return selectedUser.value?.nickname || selectedUser.value?.username || ''
})

const selectedUserShort = computed(() => {
  const u = selectedUser.value
  if (!u) return ''
  const label = u?.nickname || u?.username || String(u?.pid || '')
  const pid = u?.pid ? `PID ${u.pid}` : String(selectedUserPid.value || '')
  return [label, pid].filter(Boolean).join(' · ')
})

function parseMaybeDate(input) {
  if (!input) return null
  const d = new Date(String(input))
  if (Number.isNaN(d.getTime())) return null
  return d
}

const nowTs = computed(() => Date.now())

const userCurrentlyBanned = computed(() => {
  const u = selectedUser.value
  if (!u) return false
  if (!u.is_banned) return false
  const until = parseMaybeDate(u.banned_until)
  if (!until) return true
  return until.getTime() > nowTs.value
})

const userCurrentlyMuted = computed(() => {
  const u = selectedUser.value
  if (!u) return false
  if (!u.is_muted) return false
  const until = parseMaybeDate(u.muted_until)
  if (!until) return true
  return until.getTime() > nowTs.value
})

const userBaseAbilities = computed(() => {
  const u = selectedUser.value
  if (!u) return []

  const banned = userCurrentlyBanned.value
  const muted = userCurrentlyMuted.value

  return [
    { label: '浏览公开内容', ok: true, hint: '不需要额外授权。' },
    { label: '关注板块', ok: !banned, hint: banned ? '封禁期间不可操作。' : '需要登录；封禁会禁止关注。' },
    { label: '发帖', ok: !banned && !muted, hint: banned ? '封禁期间不可发帖。' : muted ? '禁言期间不可发帖。' : '需要登录；禁言/封禁会限制。' },
    { label: '评论', ok: !banned && !muted, hint: banned ? '封禁期间不可评论。' : muted ? '禁言期间不可评论。' : '需要登录；禁言/封禁会限制。' },
  ]
})

const selectedUser = computed(() => {
  const pid = String(selectedUserPid.value || '').trim()
  if (!pid) return null
  return users.value.find((u) => String(u?.pid || '') === pid) || null
})

const allRoles = computed(() => {
  const s = new Set()
  for (const a of assignments.value || []) {
    const r = String(a?.role || '').trim()
    if (r) s.add(r)
  }
  for (const p of policies.value || []) {
    const sub = String(p?.sub || '').trim()
    if (sub && sub.startsWith('role:')) s.add(sub)
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b))
})

const allObjs = computed(() => {
  const s = new Set()
  for (const p of policies.value || []) {
    const obj = String(p?.obj || '').trim()
    if (obj) s.add(obj)
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b))
})

const allActs = computed(() => {
  const s = new Set()
  for (const p of policies.value || []) {
    const act = String(p?.act || '').trim()
    if (act) s.add(act)
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b))
})

const userRoles = computed(() => {
  const pid = String(selectedUserPid.value || '').trim()
  if (!pid) return []

  const list = (assignments.value || [])
    .filter((a) => String(a?.user || '') === pid)
    .map((a) => ({ role: String(a?.role || ''), dom: String(a?.dom || '*') || '*' }))
    .filter((x) => x.role)

  // casbin enforcer 中对 staff 有一个“隐式” role:staff 校验：这里把它展示出来
  if (selectedUser.value?.is_staff) {
    if (!list.some((x) => x.role === 'role:staff' && (x.dom || '*') === '*')) {
      list.unshift({ role: 'role:staff', dom: '*' })
    }
  }

  return list
})

const rolePolicies = computed(() => {
  const role = String(selectedRole.value || '').trim()
  if (!role) return []
  return (policies.value || [])
    .filter((p) => String(p?.sub || '') === role)
    .map((p) => ({ sub: p.sub, dom: String(p?.dom || '*') || '*', obj: p.obj, act: p.act }))
})

function groupPoliciesByObj(items) {
  const map = new Map()
  for (const it of items || []) {
    const obj = String(it?.obj || '').trim() || '(未命名 obj)'
    if (!map.has(obj)) map.set(obj, [])
    map.get(obj).push(it)
  }
  const groups = Array.from(map.entries())
    .map(([obj, list]) => ({ obj, list: list.slice() }))
    .sort((a, b) => String(a.obj).localeCompare(String(b.obj)))
  for (const g of groups) {
    g.list.sort((a, b) => {
      return (
        String(a.dom || '').localeCompare(String(b.dom || '')) ||
        String(a.act || '').localeCompare(String(b.act || ''))
      )
    })
  }
  return groups
}

const rolePoliciesGrouped = computed(() => groupPoliciesByObj(rolePolicies.value))
const userEffectiveGrouped = computed(() => groupPoliciesByObj(userEffectivePolicies.value))

function groupBy(items, keyFn) {
  const map = new Map()
  for (const it of items || []) {
    const key = String(keyFn(it) || '')
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(it)
  }
  return Array.from(map.entries()).map(([key, list]) => ({ key, list }))
}

const userEffectiveByVia = computed(() => {
  const groups = groupBy(userEffectivePolicies.value, (x) => x?.via || '未知来源')
    .map((g) => ({
      via: g.key,
      count: g.list.length,
      objGroups: groupPoliciesByObj(g.list),
    }))
    .sort((a, b) => String(a.via).localeCompare(String(b.via)))
  return groups
})

function uniqKey(dom, obj, act) {
  return `${dom || '*'}|${obj || ''}|${act || ''}`
}

const userEffectivePolicies = computed(() => {
  const u = selectedUser.value
  const pid = String(selectedUserPid.value || '').trim()
  if (!pid) return []

  const byKey = new Map()

  // direct policies: p.sub == user pid
  for (const p of policies.value || []) {
    if (String(p?.sub || '') !== pid) continue
    const dom = String(p?.dom || '*') || '*'
    const k = uniqKey(dom, p.obj, p.act)
    if (!byKey.has(k)) byKey.set(k, { dom, obj: p.obj, act: p.act, via: '直接授权' })
  }

  // staff implicit role
  if (u?.is_staff) {
    for (const p of policies.value || []) {
      if (String(p?.sub || '') !== 'role:staff') continue
      const dom = String(p?.dom || '*') || '*'
      const k = uniqKey(dom, p.obj, p.act)
      if (!byKey.has(k)) byKey.set(k, { dom, obj: p.obj, act: p.act, via: 'role:staff（管理员）' })
    }
  }

  // via assignments: g(user, role, dom)
  for (const a of assignments.value || []) {
    if (String(a?.user || '') !== pid) continue
    const role = String(a?.role || '')
    const adom = String(a?.dom || '*') || '*'
    if (!role) continue

    for (const p of policies.value || []) {
      if (String(p?.sub || '') !== role) continue
      const pdom = String(p?.dom || '*') || '*'
      // only show policies that can be effective under this assignment
      if (!(pdom === '*' || pdom === adom)) continue
      const k = uniqKey(pdom, p.obj, p.act)
      if (!byKey.has(k)) byKey.set(k, { dom: pdom, obj: p.obj, act: p.act, via: `${role}（dom=${adom}）` })
    }
  }

  return Array.from(byKey.values()).sort((a, b) => {
    return (
      String(a.dom || '').localeCompare(String(b.dom || '')) ||
      String(a.obj || '').localeCompare(String(b.obj || '')) ||
      String(a.act || '').localeCompare(String(b.act || ''))
    )
  })
})

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [uRes, pRes, aRes] = await Promise.all([
      api.get('/api/admin/users/'),
      api.get('/api/admin/rbac/policies/'),
      api.get('/api/admin/rbac/assignments/'),
    ])
    users.value = Array.isArray(uRes?.data) ? uRes.data : []
    policies.value = Array.isArray(pRes?.data?.results) ? pRes.data.results : []
    assignments.value = Array.isArray(aRes?.data?.results) ? aRes.data.results : []

    // default selection: me
    if (!String(selectedUserPid.value || '').trim() && mePid.value) {
      selectedUserPid.value = mePid.value
    }
  } catch (e) {
    const detail = e?.response?.data?.detail
    if (e?.response?.status === 403) {
      error.value = detail || '无权限访问（需要 rbac/manage）。'
    } else {
      error.value = detail || '加载失败。'
    }
  } finally {
    loading.value = false
  }
}

async function bindRole() {
  error.value = ''
  const pid = String(selectedUserPid.value || '').trim()
  const role = String(roleBindForm.value.role || '').trim()
  const dom = String(roleBindForm.value.dom || '*').trim() || '*'
  if (!pid) {
    error.value = '请先选择用户。'
    return
  }
  if (!role) {
    error.value = '请选择或输入角色。'
    return
  }
  try {
    await api.post('/api/admin/rbac/assignments/', { user: pid, role, dom })
    roleBindForm.value = { role: '', dom: '*' }
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || '绑定失败。'
  }
}

async function unbindRole(role, dom) {
  error.value = ''
  const pid = String(selectedUserPid.value || '').trim()
  if (!pid) return
  try {
    await api.post('/api/admin/rbac/assignments/remove/', { user: pid, role, dom: dom || '*' })
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || '删除绑定失败。'
  }
}

async function addRolePolicy() {
  error.value = ''
  const role = String(selectedRole.value || '').trim()
  if (!role) {
    error.value = '请先选择角色。'
    return
  }
  const dom = String(rolePolicyForm.value.dom || '*').trim() || '*'
  const obj = String(rolePolicyForm.value.obj || '').trim()
  const act = String(rolePolicyForm.value.act || '').trim()
  if (!obj || !act) {
    error.value = '请填写 obj / act。'
    return
  }
  try {
    await api.post('/api/admin/rbac/policies/', { sub: role, dom, obj, act })
    rolePolicyForm.value = { ...rolePolicyForm.value }
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || '添加权限失败。'
  }
}

async function removeRolePolicy(p) {
  error.value = ''
  try {
    await api.post('/api/admin/rbac/policies/remove/', {
      sub: p.sub,
      dom: p.dom || '*',
      obj: p.obj,
      act: p.act,
    })
    await loadAll()
  } catch (e) {
    error.value = e?.response?.data?.detail || '删除权限失败。'
  }
}

function userLabel(u) {
  const name = u?.nickname || u?.username || ''
  const pid = u?.pid ? `PID ${u.pid}` : ''
  const extra = u?.username && u?.nickname ? ` · ${u.username}` : ''
  return [name + extra, pid].filter(Boolean).join(' · ')
}

onMounted(loadAll)
</script>

<template>
  <div class="stack">
    <div class="card">
      <div class="row" style="justify-content: space-between">
        <h2 style="margin: 0">权限管理</h2>
        <RouterLink class="btn" to="/admin">返回</RouterLink>
      </div>

      <div class="muted" style="margin-top: 8px">
        图形化视图：用户 → 角色 → 权限。选择用户后，左侧绑定角色；选择角色后，中间配置权限；右侧预览该用户的“有效权限”。
      </div>

      <div class="row" style="margin-top: 10px">
        <button class="btn" :disabled="loading" @click="loadAll">刷新</button>
        <span class="muted" v-if="loading">加载中…</span>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <div class="rbac-grid">
      <!-- 用户 -->
      <div class="card stack rbac-panel" style="gap: 10px">
        <div class="row" style="justify-content: space-between">
          <h3 style="margin: 0">
            用户
            <span v-if="selectedUserShort" class="muted" style="font-size: 12px; font-weight: 600">
              · 当前：{{ selectedUserShort }}
            </span>
          </h3>
          <span class="muted" style="font-size: 12px">选择一个用户</span>
        </div>

        <div class="stack" style="gap: 8px">
          <div class="muted" style="font-size: 12px">用户（PID）</div>
          <select v-model="selectedUserPid">
            <option value="">请选择…</option>
            <option v-for="u in users" :key="u.id" :value="String(u.pid || '')">
              {{ userLabel(u) }}
            </option>
          </select>
          <div v-if="selectedUser" class="muted" style="font-size: 12px">
            {{ selectedUser.is_superuser ? '超级管理员' : selectedUser.is_staff ? '管理员' : '普通用户' }}
            <span v-if="selectedUser.id"> · #{{ selectedUser.id }}</span>
          </div>
        </div>

        <div class="muted" style="font-weight: 700">→ 角色绑定（{{ userRoles.length }}）</div>

        <div v-if="!selectedUserPid" class="muted">请先选择用户。</div>
        <div v-else class="stack" style="gap: 10px">
          <div class="card stack" style="gap: 10px">
            <div class="muted" style="font-size: 12px">给该用户绑定角色（可按 domain 生效）</div>
            <div class="row">
              <div style="flex: 2; min-width: 200px">
                <div class="muted" style="font-size: 12px; margin-bottom: 4px">角色</div>
                <input v-model="roleBindForm.role" list="rbac-role-options" placeholder="role:staff / role:moderator" />
                <datalist id="rbac-role-options">
                  <option v-for="r in allRoles" :key="r" :value="r" />
                </datalist>
                <div class="muted" style="font-size: 12px; margin-top: 4px">建议使用 role: 前缀。</div>
              </div>
              <div style="flex: 1; min-width: 140px">
                <div class="muted" style="font-size: 12px; margin-bottom: 4px">domain</div>
                <input v-model="roleBindForm.dom" placeholder="* 或板块 slug" />
              </div>
              <button class="btn btn-solid" style="white-space: nowrap" @click="bindRole">绑定</button>
            </div>
          </div>

          <div class="stack" style="gap: 8px">
            <div class="muted" style="font-size: 12px">当前角色（点击后在中间配置权限）</div>
            <div v-if="!userRoles.length" class="muted">暂无角色绑定。</div>
            <div v-else class="stack" style="gap: 8px">
              <div class="sidenav-links">
                <div v-for="(r, idx) in userRoles" :key="idx" class="row" style="justify-content: space-between; gap: 8px">
                  <button
                    class="sidenav-link"
                    type="button"
                    :class="{ 'is-active': selectedRole === r.role }"
                    style="flex: 1; min-width: 0"
                    @click="selectedRole = r.role"
                  >
                    <span style="font-weight: 700">{{ r.role }}</span>
                    <span class="muted" style="margin-left: auto; font-size: 12px">dom={{ r.dom || '*' }}</span>
                  </button>
                  <button
                    v-if="!(r.role === 'role:staff' && (r.dom || '*') === '*')"
                    class="btn"
                    type="button"
                    @click="unbindRole(r.role, r.dom)"
                  >
                    移除
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 角色 -->
      <div class="card stack rbac-panel" style="gap: 10px">
        <div class="row" style="justify-content: space-between">
          <h3 style="margin: 0">
            角色
            <span v-if="selectedRole" class="muted" style="font-size: 12px; font-weight: 600">· 当前：{{ selectedRole }}</span>
          </h3>
          <span class="muted" style="font-size: 12px">角色 → 权限</span>
        </div>

        <div class="stack" style="gap: 8px">
          <div class="muted" style="font-size: 12px">选择角色</div>
          <select v-model="selectedRole">
            <option value="">请选择…</option>
            <option v-for="r in allRoles" :key="r" :value="r">{{ r }}</option>
          </select>
          <div class="muted" style="font-size: 12px">提示：建议用 role: 前缀（例如 role:staff）。</div>
        </div>

        <div class="muted" style="font-weight: 700">→ 权限配置（{{ rolePolicies.length }}）</div>

        <div v-if="!selectedRole" class="muted">请先选择角色。</div>
        <div v-else class="stack" style="gap: 10px">
          <div class="card stack" style="gap: 10px">
            <div class="muted" style="font-size: 12px">给角色添加权限（p, sub, dom, obj, act）</div>
            <div class="row">
              <div style="flex: 1; min-width: 140px">
                <div class="muted" style="font-size: 12px; margin-bottom: 4px">domain</div>
                <input v-model="rolePolicyForm.dom" placeholder="* 或板块 slug" />
              </div>
              <div style="flex: 1; min-width: 160px">
                <div class="muted" style="font-size: 12px; margin-bottom: 4px">obj</div>
                <input v-model="rolePolicyForm.obj" list="rbac-obj-options" placeholder="例如 admin.users" />
                <datalist id="rbac-obj-options">
                  <option v-for="o in allObjs" :key="o" :value="o" />
                </datalist>
              </div>
              <div style="flex: 1; min-width: 160px">
                <div class="muted" style="font-size: 12px; margin-bottom: 4px">act</div>
                <input v-model="rolePolicyForm.act" list="rbac-act-options" placeholder="例如 read" />
                <datalist id="rbac-act-options">
                  <option v-for="a in allActs" :key="a" :value="a" />
                </datalist>
              </div>
              <button class="btn btn-solid" style="white-space: nowrap" @click="addRolePolicy">添加</button>
            </div>
          </div>

          <div class="stack" style="gap: 8px">
            <div class="muted" style="font-size: 12px">当前权限（按 obj 分组）</div>
            <div v-if="!rolePolicies.length" class="muted">暂无权限。</div>
            <div v-else class="stack" style="gap: 8px">
              <div v-for="g in rolePoliciesGrouped" :key="g.obj" class="card" style="padding: 10px">
                <div class="row" style="justify-content: space-between">
                  <div style="font-weight: 800">{{ g.obj }}</div>
                  <div class="muted" style="font-size: 12px">{{ g.list.length }} 项</div>
                </div>
                <div class="stack" style="gap: 6px; margin-top: 8px">
                  <div v-for="(p, idx) in g.list" :key="idx" class="row" style="justify-content: space-between; gap: 8px">
                    <div style="min-width: 0">
                      <div style="font-weight: 700">{{ p.act }}</div>
                      <div class="muted" style="font-size: 12px">dom={{ p.dom || '*' }}</div>
                    </div>
                    <button class="btn" type="button" @click="removeRolePolicy(p)">删除</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 有效权限 -->
      <div class="card stack rbac-panel" style="gap: 10px">
        <div class="row" style="justify-content: space-between">
          <h3 style="margin: 0">
            有效权限
            <span v-if="selectedUserShort" class="muted" style="font-size: 12px; font-weight: 600">· 当前：{{ selectedUserShort }}</span>
          </h3>
          <span class="muted" style="font-size: 12px">预览</span>
        </div>

        <div v-if="!selectedUserPid" class="muted">请选择用户后查看。</div>
        <div v-else class="stack" style="gap: 8px">
          <div class="muted" style="font-size: 12px">
            用户：{{ selectedUserName || selectedUserPid }}
          </div>
          <div v-if="!userEffectivePolicies.length" class="muted">暂无有效权限。</div>
          <div v-else class="stack" style="gap: 8px">
            <div class="muted" style="font-size: 12px">共 {{ userEffectivePolicies.length }} 项（先按来源聚合，再按 obj 分组）</div>

            <div v-for="viaGroup in userEffectiveByVia" :key="viaGroup.via" class="card" style="padding: 10px">
              <div class="row" style="justify-content: space-between">
                <div style="font-weight: 800">来源：{{ viaGroup.via }}</div>
                <div class="muted" style="font-size: 12px">{{ viaGroup.count }} 项</div>
              </div>

              <div class="stack" style="gap: 8px; margin-top: 8px">
                <div v-for="g in viaGroup.objGroups" :key="g.obj" class="card" style="padding: 10px">
                  <div class="row" style="justify-content: space-between">
                    <div style="font-weight: 800">{{ g.obj }}</div>
                    <div class="muted" style="font-size: 12px">{{ g.list.length }} 项</div>
                  </div>
                  <div class="stack" style="gap: 6px; margin-top: 8px">
                    <div v-for="(x, idx) in g.list" :key="idx" class="row" style="justify-content: space-between; gap: 8px">
                      <div style="min-width: 0">
                        <div style="font-weight: 700">{{ x.act }}</div>
                        <div class="muted" style="font-size: 12px">dom={{ x.dom || '*' }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rbac-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.rbac-panel {
  min-height: 0;
  max-height: calc(100vh - 220px);
  overflow: auto;
}

.rbac-panel :deep(h3) {
  line-height: 1.2;
}

@media (max-width: 1000px) {
  .rbac-grid {
    grid-template-columns: 1fr;
  }

  .rbac-panel {
    max-height: none;
    overflow: visible;
  }
}
</style>
