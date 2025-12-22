<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth'

const router = useRouter()

onMounted(async () => {
  await auth.loadMe()
})

async function logout() {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2 style="margin: 0 0 6px">我的账号</h2>
      <div v-if="!auth.state.me" class="muted">未登录</div>
      <div v-else class="stack" style="gap: 8px">
        <div class="row">
          <div><b>用户名：</b>{{ auth.state.me.username }}</div>
          <div class="muted">Lv{{ auth.state.me.level }}（活跃度：{{ auth.state.me.activity_score }}）</div>
        </div>
        <div class="row">
          <div><b>今日下载：</b>{{ auth.state.me.downloads_today }} / {{ auth.state.me.daily_download_limit }}</div>
          <div><b>剩余：</b>{{ auth.state.me.downloads_remaining_today }}</div>
        </div>
        <div v-if="auth.state.me.is_banned" class="card" style="border-color: #fecaca; background: #fff1f2">
          <b>账号已封禁</b>
          <div class="muted">原因：{{ auth.state.me.ban_reason || '未填写' }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="row">
        <RouterLink class="btn" to="/">返回板块</RouterLink>
        <button v-if="auth.state.me" class="btn" @click="logout">退出登录</button>
      </div>
    </div>
  </div>
</template>
