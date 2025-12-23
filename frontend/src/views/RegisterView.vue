<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth'
import { api } from '../api'

const router = useRouter()

const nickname = ref('')
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

function normalizeHandle(v) {
  const s = String(v || '').trim().toLowerCase()
  return s
}

function validateNickname(v) {
  const s = String(v || '').trim()
  if (!s) return '昵称必填。'
  if (s.length > 20) return '昵称长度不能超过 20。'
  if (s.includes('<') || s.includes('>')) return '昵称不允许包含 < 或 >。'
  return ''
}

function validateHandle(v) {
  const s = normalizeHandle(v)
  if (!s) return '用户名必填。'
  if (s.length > 20) return '用户名长度不能超过 20。'
  if (!s.startsWith('@')) return '用户名必须以 @ 开头。'
  if (!/^@[a-z0-9_]+$/.test(s)) return '用户名仅允许字母/数字/下划线。'
  return ''
}

function translateBackendMessage(msg) {
  if (!msg) return msg
  const m = String(msg)

  // Django password validators
  if (m.includes('This field is required')) return '必填。'
  if (m.includes('too short') && m.includes('at least')) return '至少 8 位。'
  if (m.includes('too common')) return '太常见。'
  if (m.includes('entirely numeric')) return '不能纯数字。'
  if (m.includes('too similar')) return '与用户名太像。'

  // Common field validations
  if (m.includes('A user with that username already exists')) return '已被占用。'
  if (m.includes('user with this username already exists')) return '已被占用。'

  return m
}

const serverCheck = ref({ state: 'idle', errors: [] })
// state: idle | checking | ok | bad

let checkTimer = null
watch([username, email, password], () => {
  if (checkTimer) clearTimeout(checkTimer)
  const p = password.value || ''
  if (!p) {
    serverCheck.value = { state: 'idle', errors: [] }
    return
  }

  checkTimer = setTimeout(async () => {
    serverCheck.value = { state: 'checking', errors: [] }
    try {
      const { data } = await api.post('/api/auth/password/check/', {
        username: normalizeHandle(username.value),
        email: (email.value || '').trim(),
        password: p,
      })
      if (data && data.ok) serverCheck.value = { state: 'ok', errors: [] }
      else serverCheck.value = { state: 'ok', errors: [] }
    } catch (e) {
      const errs = e?.response?.data?.password
      serverCheck.value = {
        state: 'bad',
        errors: Array.isArray(errs) ? errs : [],
      }
    }
  }, 300)
})

const passwordRules = computed(() => {
  const p = password.value || ''
  return [
    { key: 'len', text: '不少于 8 位', ok: p.length >= 8 },
    { key: 'lower', text: '包含小写字母', ok: /[a-z]/.test(p) },
    { key: 'upper', text: '包含大写字母', ok: /[A-Z]/.test(p) },
    { key: 'digit', text: '包含数字', ok: /\d/.test(p) },
  ]
})

const passwordRulesOk = computed(() => passwordRules.value.every((r) => r.ok))

const passwordServerOk = computed(() => serverCheck.value.state === 'ok')
const passwordOverallOk = computed(() => {
  if (serverCheck.value.state === 'ok') return true
  if (serverCheck.value.state === 'bad') return false
  return passwordRulesOk.value
})
const passwordServerText = computed(() => {
  if (serverCheck.value.state === 'idle') return '后端校验：请输入密码'
  if (serverCheck.value.state === 'checking') return '后端校验：校验中…'
  if (serverCheck.value.state === 'ok') return '后端校验：通过'
  // bad
  const msg = (serverCheck.value.errors || []).map(translateBackendMessage).join('；')
  return msg ? `后端校验：未通过（${msg}）` : '后端校验：未通过'
})

function formatRegisterError(e) {
  // 网络/代理错误（后端没启动、8000 不通）
  if (!e?.response) {
    return '无法连接后端（确认后端已启动且 127.0.0.1:8000 可访问）。'
  }

  const data = e.response.data
  if (!data) return '注册失败。'
  if (typeof data === 'string') return data
  if (typeof data?.detail === 'string') return data.detail

  const translate = translateBackendMessage

  const fieldName = {
    nickname: '昵称',
    username: '用户名',
    email: '邮箱',
    password: '密码',
  }

  const parts = []
  for (const [key, value] of Object.entries(data)) {
    const label = fieldName[key] || key
    if (Array.isArray(value)) parts.push(`${label}：${value.map(translate).join('；')}`)
    else if (value && typeof value === 'object') parts.push(`${label}：${JSON.stringify(value)}`)
    else parts.push(`${label}：${translate(value)}`)
  }
  return parts.join('\n') || '注册失败。'
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const nickErr = validateNickname(nickname.value)
    if (nickErr) {
      error.value = nickErr
      return
    }
    const handleErr = validateHandle(username.value)
    if (handleErr) {
      error.value = handleErr
      return
    }

    const uname = normalizeHandle(username.value)
    await auth.register({
      nickname: nickname.value.trim(),
      username: uname,
      email: email.value.trim(),
      password: password.value,
    })
    await router.push('/')
  } catch (e) {
    error.value = formatRegisterError(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card stack" style="max-width: 520px; margin: 0 auto">
    <h2 style="margin: 0">注册</h2>

    <div class="stack">
      <label class="stack" style="gap: 6px">
        <div>昵称</div>
        <input v-model="nickname" autocomplete="nickname" maxlength="20" />
        <div class="muted" style="font-size: 12px">昵称可重复；用于全站展示。</div>
      </label>
      <label class="stack" style="gap: 6px">
        <div>用户名（@开头）</div>
        <input v-model="username" autocomplete="username" maxlength="20" placeholder="@username" />
        <div class="muted" style="font-size: 12px">仅字母/数字/下划线；大小写不敏感；全站唯一。</div>
      </label>
      <label class="stack" style="gap: 6px">
        <div>邮箱（可选）</div>
        <input v-model="email" type="email" autocomplete="email" />
      </label>

      <div v-if="password" class="card" style="padding: 8px; font-size: 13px; line-height: 1.35">
        <div class="muted" style="margin-bottom: 6px">
          密码校验：
          <span :style="{ color: passwordOverallOk ? '#16a34a' : '#dc2626', fontWeight: 600 }">
            {{ passwordOverallOk ? '通过' : '未通过' }}
          </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 10px">
          <div
            v-for="r in passwordRules"
            :key="r.key"
            :style="{ color: r.ok ? '#16a34a' : '#dc2626' }"
          >
            {{ r.ok ? '✓' : '✗' }} {{ r.text }}
          </div>

          <div
            style="grid-column: 1 / -1"
            :style="{
              color:
                serverCheck.state === 'checking' || serverCheck.state === 'idle'
                  ? '#6b7280'
                  : passwordServerOk
                    ? '#16a34a'
                    : '#dc2626',
            }"
          >
            {{ passwordServerOk ? '✓' : serverCheck.state === 'checking' ? '…' : '✗' }} {{ passwordServerText }}
          </div>
        </div>
      </div>
      <label class="stack" style="gap: 6px">
        <div>密码</div>
        <input v-model="password" type="password" autocomplete="new-password" />
      </label>

      <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2; white-space: pre-line">
        {{ error }}
      </div>

      <button class="btn btn-primary" :disabled="loading" @click="submit">
        {{ loading ? '注册中…' : '注册并登录' }}
      </button>
    </div>
  </div>
</template>
