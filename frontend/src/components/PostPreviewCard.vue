<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  post: { type: Object, required: true },
  meta: { type: String, default: '' },
  titleHtml: { type: String, default: '' },
  showViews: { type: Boolean, default: true },
})

const to = computed(() => `/posts/${props.post?.id}`)
const views = computed(() => Number(props.post?.views_count || 0))
const authorUsername = computed(() => props.post?.author_username || '')
const authorPid = computed(() => String(props.post?.author_pid || '').trim())
const authorHandle = computed(() => {
  const raw = String(authorUsername.value || '')
  const u = raw.replace(/^@+/, '')
  return u ? `@${u}` : ''
})

const router = useRouter()

function goToAuthor(e) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  if (!authorPid.value) return
  router.push(`/u/${authorPid.value}`)
}
</script>

<template>
  <RouterLink :to="to" class="bili-card">
    <div class="bili-card-cover">
      <img v-if="post?.cover_image_url" :src="post.cover_image_url" loading="lazy" />
      <div v-if="showViews" class="bili-stats">
        <span class="stat-item">
          <svg viewBox="0 0 12 12" width="12" height="12" fill="currentColor">
            <path
              d="M6 3.5C3.5 3.5 1.5 6 1.5 6s2 2.5 4.5 2.5S10.5 6 10.5 6 8.5 3.5 6 3.5zM6 7a1 1 0 110-2 1 1 0 010 2z"
            />
          </svg>
          {{ views }}
        </span>
      </div>
    </div>

    <div class="bili-card-info">
      <div v-if="titleHtml" class="bili-title" :title="post?.title" v-html="titleHtml"></div>
      <div v-else class="bili-title" :title="post?.title">{{ post?.title }}</div>

      <div v-if="meta" class="muted bili-meta">{{ meta }}</div>

      <div class="bili-author">
        <button type="button" class="bili-author-link" @click="goToAuthor">By {{ authorHandle }}</button>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.bili-card {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
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

.bili-meta {
  font-size: 12px;
  margin-top: 4px;
}

.bili-author {
  font-size: 12px;
  color: #9499a0;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.bili-author-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.bili-author-link:hover {
  color: #00aeec;
}
</style>
