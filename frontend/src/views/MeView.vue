<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const router = useRouter()

const error = ref('')
const actionLoading = ref(false)

const postsLoading = ref(false)
const postsError = ref('')
const posts = ref([])
const postsNext = ref('')

const bioDraft = ref('')
const nicknameDraft = ref('')
const usernameDraft = ref('')

const currentPassword = ref('')
const newPassword1 = ref('')
const newPassword2 = ref('')

const me = computed(() => auth.state.me)

const meInitial = computed(() => {
  const s = (me.value?.nickname || me.value?.username || '').trim()
  return s ? s.slice(0, 1).toUpperCase() : 'U'
})

function normalizeHandle(v) {
  return String(v || '').trim().toLowerCase()
}

function formatApiError(e, fallback = '操作失败。') {
  const data = e?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (typeof data?.detail === 'string') return data.detail
  const parts = []
  for (const [k, v] of Object.entries(data)) {
    if (Array.isArray(v)) parts.push(`${k}：${v.join('；')}`)
    else parts.push(`${k}：${String(v)}`)
  }
  return parts.join('\n') || fallback
}

async function loadPosts(url = '/api/me/posts/') {
  if (!auth.isAuthed()) return
  postsLoading.value = true
  postsError.value = ''
  try {
    const { data } = await api.get(url)
    const items = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []
    if (url === '/api/me/posts/') posts.value = items
    else posts.value = [...(posts.value || []), ...items]
    postsNext.value = data?.next || ''
  } catch (e) {
    postsError.value = formatApiError(e, '发帖历史加载失败。')
  } finally {
    postsLoading.value = false
  }
}

async function refreshMe() {
  await auth.loadMe()
  bioDraft.value = me.value?.bio || ''
  nicknameDraft.value = me.value?.nickname || ''
  usernameDraft.value = me.value?.username || ''
}

onMounted(async () => {
  error.value = ''
  if (!auth.isAuthed()) return
  await refreshMe()
  await loadPosts()
})

async function logout() {
  auth.logout()
  await router.push('/login')
}

async function checkin() {
  if (!auth.isAuthed()) {
    error.value = '请先登录。'
    return
  }
  actionLoading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/api/me/checkin/')
    // Keep local state consistent.
    if (me.value) {
      me.value.checked_in_today = true
      if (typeof data?.plcoin === 'number') me.value.plcoin = data.plcoin
      if (typeof data?.plcoin === 'number') me.value.activity_score = data.plcoin
    }
  } catch (e) {
    error.value = formatApiError(e, '签到失败。')
  } finally {
    actionLoading.value = false
  }
}

async function saveBio() {
  actionLoading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/api/me/bio/', { bio: String(bioDraft.value || '') })
    if (me.value) me.value.bio = data?.bio ?? bioDraft.value
  } catch (e) {
    error.value = formatApiError(e, '保存简介失败。')
  } finally {
    actionLoading.value = false
  }
}

async function saveNickname() {
  actionLoading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/api/me/nickname/', { nickname: String(nicknameDraft.value || '').trim() })
    if (me.value) {
      if (typeof data?.nickname === 'string') me.value.nickname = data.nickname
      if (typeof data?.plcoin === 'number') {
        me.value.plcoin = data.plcoin
        me.value.activity_score = data.plcoin
      }
      if (typeof data?.used === 'number') me.value.nickname_changes_used = data.used
    }
  } catch (e) {
    error.value = formatApiError(e, '修改昵称失败。')
  } finally {
    actionLoading.value = false
  }
}

async function saveUsername() {
  actionLoading.value = true
  error.value = ''
  try {
    const u = normalizeHandle(usernameDraft.value)
    const { data } = await api.post('/api/me/username/', { username: u })
    if (me.value) {
      if (typeof data?.username === 'string') me.value.username = data.username
      if (typeof data?.plcoin === 'number') {
        me.value.plcoin = data.plcoin
        me.value.activity_score = data.plcoin
      }
      if (typeof data?.used === 'number') me.value.username_changes_used = data.used
    }
  } catch (e) {
    error.value = formatApiError(e, '修改用户名失败。')
  } finally {
    actionLoading.value = false
  }
}

async function changePassword() {
  if (!auth.isAuthed()) {
    error.value = '请先登录。'
    return
  }
  if (!confirm('确定要修改密码吗？修改后需要重新登录。')) return

  actionLoading.value = true
  error.value = ''
  try {
    await api.post('/api/me/password/', {
      current_password: String(currentPassword.value || ''),
      new_password1: String(newPassword1.value || ''),
      new_password2: String(newPassword2.value || ''),
    })

    currentPassword.value = ''
    newPassword1.value = ''
    newPassword2.value = ''

    auth.logout()
    await router.push('/login')
  } catch (e) {
    error.value = formatApiError(e, '修改密码失败。')
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2 style="margin: 0 0 6px">我的账号</h2>
      <div v-if="!auth.isAuthed()" class="muted">未登录</div>

      <div v-else-if="auth.state.loading" class="muted">加载中…</div>

      <div v-else-if="!me" class="muted">未登录</div>

      <div v-else class="stack" style="gap: 10px">
        <div class="row" style="align-items: center; justify-content: space-between">
          <div class="row" style="gap: 10px; align-items: center">
            <div style="width: 48px; height: 48px">
              <img
                v-if="me.avatar_url"
                :src="me.avatar_url"
                alt="avatar"
                style="width: 48px; height: 48px; border-radius: 999px; object-fit: cover; border: 1px solid #e5e7eb"
              />
              <div
                v-else
                style="width: 48px; height: 48px; border-radius: 999px; border: 1px solid #e5e7eb; display: flex; align-items: center; justify-content: center; font-weight: 700"
              >
                {{ meInitial }}
              </div>
            </div>
            <div class="stack" style="gap: 2px">
              <div style="font-weight: 700; font-size: 16px">{{ me.nickname || '用户' }}</div>
              <div class="muted" style="font-size: 13px">{{ me.username }} · PID {{ me.pid }}</div>
            </div>
          </div>

          <div class="row" style="gap: 8px">
            <button class="btn btn-primary" type="button" :disabled="actionLoading || me.checked_in_today" @click="checkin">
              {{ me.checked_in_today ? '今日已签到' : '签到 +2' }}
            </button>
          </div>
        </div>

        <div class="row" style="justify-content: space-between">
          <div><b>PLCoin：</b>{{ me.plcoin }}</div>
          <div class="muted">Lv{{ me.level }}（活跃度：{{ me.activity_score }}）</div>
        </div>

        <div class="row" style="justify-content: space-between">
          <div><b>累计登录天数：</b>{{ me.login_days }}</div>
          <div class="muted">今日发帖积分：{{ me.post_points_earned_today }} / {{ me.post_points_daily_cap }}</div>
        </div>

        <div class="row" style="justify-content: space-between">
          <div><b>今日下载：</b>{{ me.downloads_today }} / {{ me.daily_download_limit }}</div>
          <div><b>剩余：</b>{{ me.downloads_remaining_today }}</div>
        </div>

        <div v-if="me.is_banned" class="card" style="border-color: #fecaca; background: #fff1f2">
          <b>账号已封禁</b>
          <div class="muted">原因：{{ me.ban_reason || '未填写' }}</div>
        </div>
      </div>
    </div>

    <div v-if="me" class="card stack">
      <h3 style="margin: 0">个人简介</h3>
      <textarea v-model="bioDraft" rows="4" placeholder="写点什么（最多 200 字）"></textarea>
      <div class="row" style="justify-content: space-between; align-items: center">
        <div class="muted" style="font-size: 12px">不允许包含 &lt; 或 &gt;。</div>
        <button class="btn" type="button" :disabled="actionLoading" @click="saveBio">保存简介</button>
      </div>
    </div>

    <div v-if="me" class="card stack">
      <h3 style="margin: 0">修改昵称 / 用户名</h3>
      <div class="row" style="gap: 10px; align-items: flex-end; flex-wrap: wrap">
        <label class="stack" style="gap: 6px; min-width: 220px">
          <div>昵称</div>
          <input v-model="nicknameDraft" maxlength="20" />
          <div class="muted" style="font-size: 12px">
            消耗：{{ me.nickname_change_cost }} PLCoin · 本年：{{ me.nickname_changes_used }}/{{ me.nickname_changes_limit }}
          </div>
        </label>
        <button class="btn" type="button" :disabled="actionLoading" @click="saveNickname">保存昵称</button>
      </div>

      <div class="row" style="gap: 10px; align-items: flex-end; flex-wrap: wrap; margin-top: 6px">
        <label class="stack" style="gap: 6px; min-width: 220px">
          <div>用户名（@开头）</div>
          <input v-model="usernameDraft" maxlength="20" placeholder="@username" />
          <div class="muted" style="font-size: 12px">
            消耗：{{ me.username_change_cost }} PLCoin · 本年：{{ me.username_changes_used }}/{{ me.username_changes_limit }}
          </div>
        </label>
        <button class="btn" type="button" :disabled="actionLoading" @click="saveUsername">保存用户名</button>
      </div>
    </div>

    <div v-if="me" class="card stack">
      <h3 style="margin: 0">修改密码</h3>
      <div class="row" style="gap: 10px; flex-wrap: wrap">
        <label class="stack" style="gap: 6px; min-width: 220px">
          <div>当前密码</div>
          <input v-model="currentPassword" type="password" autocomplete="current-password" />
        </label>
        <label class="stack" style="gap: 6px; min-width: 220px">
          <div>新密码</div>
          <input v-model="newPassword1" type="password" autocomplete="new-password" />
        </label>
        <label class="stack" style="gap: 6px; min-width: 220px">
          <div>确认新密码</div>
          <input v-model="newPassword2" type="password" autocomplete="new-password" />
        </label>
        <button class="btn" type="button" :disabled="actionLoading" @click="changePassword">修改密码</button>
      </div>
      <div class="muted" style="font-size: 12px">提交前会二次确认，成功后需重新登录。</div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2; white-space: pre-line">
      {{ error }}
    </div>

    <div v-if="me" class="card stack">
      <div class="row" style="justify-content: space-between; align-items: center">
        <h3 style="margin: 0">发帖历史</h3>
        <button class="btn" type="button" :disabled="postsLoading" @click="loadPosts('/api/me/posts/')">刷新</button>
      </div>
      <div v-if="postsError" class="muted" style="color: #b91c1c; white-space: pre-line">{{ postsError }}</div>
      <div v-if="postsLoading" class="muted">加载中…</div>
      <div v-else-if="!posts.length" class="muted">还没有发过帖子。</div>
      <div v-else class="stack" style="gap: 8px">
        <div v-for="p in posts" :key="p.id" class="card" style="background: #fafafa">
          <div class="row" style="justify-content: space-between; gap: 10px">
            <div class="stack" style="gap: 2px; min-width: 0">
              <RouterLink :to="`/posts/${p.id}`" style="font-weight: 600; text-decoration: none; color: inherit">
                {{ p.title }}
              </RouterLink>
              <div class="muted" style="font-size: 12px">
                {{ new Date(p.created_at).toLocaleString() }}
              </div>
            </div>
            <RouterLink class="btn" :to="`/posts/${p.id}/edit`">编辑</RouterLink>
          </div>
        </div>

        <button v-if="postsNext" class="btn" type="button" :disabled="postsLoading" @click="loadPosts(postsNext)">
          加载更多
        </button>
      </div>
    </div>

    <div class="card">
      <div class="row">
        <RouterLink class="btn" to="/">返回板块</RouterLink>
        <button v-if="me" class="btn" type="button" @click="logout">退出登录</button>
      </div>
    </div>
  </div>
</template>
