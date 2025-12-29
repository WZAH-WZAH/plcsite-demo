<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PostActionBar from './PostActionBar.vue'

const props = defineProps({
  post: { type: Object, required: true },
})

const router = useRouter()

function goToDetail() {
  if (window.getSelection().toString().length > 0) return
  router.push(`/posts/${props.post.id}`)
}

function goToProfile() {
  const pid = props.post?.author_pid
  if (!pid) return
  router.push(`/u/${pid}`)
}

// 昵称优先
const displayName = computed(() => props.post.author_nickname || props.post.author_username)
const handle = computed(() => String(props.post.author_username || '').replace(/^@+/, ''))

const generatedExcerpt = computed(() => {
  if (props.post.excerpt) return props.post.excerpt
  const text = props.post.body || ''
  const cleanText = text.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
  return cleanText.length > 140 ? cleanText.slice(0, 140) + '...' : cleanText
})

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const diff = (new Date() - date) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + 'm'
  if (diff < 86400) return Math.floor(diff / 3600) + 'h'
  return date.getMonth() + 1 + '月' + date.getDate() + '日'
}
</script>

<template>
  <div class="tl-item" @click="goToDetail">
    <div class="tl-avatar-col">
      <div class="tl-avatar" @click.stop="goToProfile">
        <img v-if="post.author_avatar" :src="post.author_avatar" class="avatar-img" />
        <span v-else class="avatar-text">{{ displayName?.[0]?.toUpperCase() }}</span>
      </div>
    </div>

    <div class="tl-content">
      <div class="tl-header">
        <span class="tl-name" @click.stop="goToProfile">{{ displayName }}</span>
        <span v-if="handle" class="tl-meta">@{{ handle }}</span>
        <span class="tl-dot">·</span>
        <span class="tl-meta">{{ formatTime(post.created_at) }}</span>
      </div>

      <div class="tl-text">
        <span class="tl-title">{{ post.title }}</span>
        {{ generatedExcerpt }}

        <div v-if="post.tags_details && post.tags_details.length" class="tags-row">
          <span
            v-for="tag in post.tags_details"
            :key="tag.id"
            class="tag-pill"
            @click.stop="router.push(`/topic/${tag.name}`)"
          >
            #{{ tag.name }}
          </span>
        </div>
      </div>

      <div v-if="post.cover_image_url" class="tl-media" @click.stop="goToDetail">
        <img :src="post.cover_image_url" loading="lazy" />
      </div>

      <PostActionBar :post="post" />
    </div>
  </div>
</template>

<style scoped>
.tl-item {
  display: flex;
  padding: 12px 16px;
  border-bottom: 1px solid #eff3f4;
  cursor: pointer;
  background: #fff;
  transition: background-color 0.2s;
}

.tl-item:hover {
  background-color: #f7f9f9;
}

.tl-avatar-col {
  margin-right: 12px;
  flex-shrink: 0;
}

.tl-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
}

.tl-avatar:hover {
  opacity: 0.85;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-text {
  font-weight: 700;
  color: #6b7280;
}

.tl-content {
  flex: 1;
  min-width: 0;
}

.tl-header {
  display: flex;
  align-items: baseline;
  font-size: 15px;
  line-height: 20px;
  margin-bottom: 2px;
}

.tl-name {
  font-weight: 700;
  color: #0f1419;
  margin-right: 4px;
}

.tl-name:hover {
  text-decoration: underline;
}

.tl-meta,
.tl-dot {
  color: #536471;
  font-size: 15px;
}

.tl-dot {
  margin: 0 4px;
}

.tl-text {
  font-size: 15px;
  line-height: 20px;
  color: #0f1419;
  margin-bottom: 10px;
  word-wrap: break-word;
}

.tl-title {
  font-weight: 700;
  margin-right: 6px;
}

.tags-row {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-pill {
  color: #00aeec;
  font-size: 13px;
  cursor: pointer;
}

.tag-pill:hover {
  text-decoration: underline;
}

.tl-media {
  margin-top: 10px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  width: 100%;
}

.tl-media img {
  width: 100%;
  height: auto;
  max-height: 500px;
  object-fit: cover;
  display: block;
}
</style>