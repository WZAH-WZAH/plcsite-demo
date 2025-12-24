<script setup>
import { auth } from '../auth'
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2 style="margin: 0 0 6px">管理</h2>
      <div class="muted">仅管理员可见（is_staff）。</div>
    </div>

    <div v-if="!auth.state.me?.is_staff" class="card" style="border-color: #fecaca; background: #fff1f2">
      无权限。
    </div>

    <div v-else class="card stack">
      <div class="row">
        <RouterLink class="btn" to="/admin/moderation">审核队列</RouterLink>
        <RouterLink class="btn" to="/admin/users">用户封禁</RouterLink>
        <RouterLink class="btn" to="/admin/audit">审核日志</RouterLink>
      </div>
    </div>
  </div>
</template>
