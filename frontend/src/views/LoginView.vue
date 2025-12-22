<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '../auth'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    await router.push(route.query.next || '/')
  } catch (e) {
    error.value = e?.response?.data?.detail || '登录失败，请检查用户名/密码。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card stack" style="max-width: 520px; margin: 0 auto">
    <h2 style="margin: 0">登录</h2>
    <div class="muted">使用账号登录后可下载/发帖/管理。</div>

    <div class="stack">
      <label class="stack" style="gap: 6px">
        <div>用户名</div>
        <input v-model="username" autocomplete="username" />
      </label>
      <label class="stack" style="gap: 6px">
        <div>密码</div>
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>

      <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">
        {{ error }}
      </div>

      <button class="btn btn-primary" :disabled="loading" @click="submit">
        {{ loading ? '登录中…' : '登录' }}
      </button>

      <div class="row">
        <span class="muted">没有账号？</span>
        <RouterLink to="/register" class="btn">去注册</RouterLink>
      </div>
    </div>
  </div>
</template>
