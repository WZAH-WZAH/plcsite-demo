<script setup>
import { onMounted } from 'vue'
import MainLayout from './layouts/MainLayout.vue'
import { auth } from './auth'

onMounted(async () => {
  await auth.loadMe()
})
</script>

<template>
  <MainLayout />
</template>
