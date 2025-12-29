<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  post: { type: Object, required: true },
})

const router = useRouter()

// 数字格式化
function formatNumber(num) {
  if (!num) return '0'
  const n = Number(num)
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toString()
}

const formattedViews = computed(() => formatNumber(props.post.views_count))
const authorPid = computed(() => String(props.post?.author_pid || '').trim())
// 优先显示昵称
const displayName = computed(() => props.post.author_nickname || props.post.author_username)

function goToProfile(e) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  if (!authorPid.value) return
  router.push(`/u/${authorPid.value}`)
}
</script>

<template>
  <RouterLink :to="`/posts/${post.id}`" class="bili-card">
    <div class="bili-card-cover">
      <img v-if="post.cover_image_url" :src="post.cover_image_url" loading="lazy" :alt="post.title" />
      <div class="bili-stats">
        <span class="stat-item">
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          <span style="margin-left: 4px">{{ formattedViews }}</span>
        </span>
      </div>
    </div>
    <div class="bili-card-info">
      <div class="bili-title" :title="post.title">{{ post.title }}</div>

      <div v-if="post.tags_details && post.tags_details.length" class="tags-row">
        <span
          v-for="tag in post.tags_details"
          :key="tag.id"
          class="tag-pill"
          @click.prevent.stop="router.push(`/topic/${tag.name}`)"
        >
          #{{ tag.name }}
        </span>
      </div>

      <button class="bili-author" type="button" @click="goToProfile">By {{ displayName }}</button>
    </div>
  </RouterLink>
</template>

<style scoped>
.bili-card {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.bili-card-cover {
  position: relative;
  width: 100%;
  height: 0;
  padding-bottom: 62.5%;
  background: #f1f2f3;
  border-radius: 6px;
  overflow: hidden;
}

.bili-card-cover img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s ease;
}

.bili-card:hover .bili-card-cover img {
  transform: scale(1.05);
}

.bili-stats {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 30px 8px 6px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6), transparent);
  color: #fff;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.bili-card-info {
  margin-top: 8px;
}

.bili-title {
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  color: #18191c;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  transition: color 0.2s;
}

.bili-card:hover .bili-title {
  color: #00aeec;
}

.bili-author {
  font-size: 12px;
  color: #9499a0;
  margin-top: 4px;
  display: flex;
  align-items: center;
  transition: color 0.2s;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.bili-author:hover {
  color: #00aeec;
}

.tags-row {
  margin-top: 6px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-pill {
  font-size: 12px;
  color: #00aeec;
  cursor: pointer;
}

.tag-pill:hover {
  text-decoration: underline;
}
</style>
