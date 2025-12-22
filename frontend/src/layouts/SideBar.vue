<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { auth } from '../auth'

const route = useRoute()
const isAdmin = computed(() => Boolean(auth.state.me?.is_staff))

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <aside class="sidenav">
    <nav class="sidenav-links" aria-label="站点导航">
      <RouterLink :class="['sidenav-link', isActive('/') ? 'is-active' : '']" to="/">首页</RouterLink>
      <RouterLink :class="['sidenav-link', isActive('/boards') ? 'is-active' : '']" to="/boards">板块</RouterLink>
      <RouterLink :class="['sidenav-link', isActive('/me') ? 'is-active' : '']" to="/me">我的</RouterLink>

      <RouterLink v-if="isAdmin" :class="['sidenav-link', isActive('/admin') ? 'is-active' : '']" to="/admin">
        管理
      </RouterLink>
    </nav>

    <div class="muted sidenav-hint">
      提示：这是通用内容站结构；外观可后续再做。
    </div>
  </aside>
</template>
