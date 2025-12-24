<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const props = defineProps({
  post: { type: Object, required: true },
  isDetail: { type: Boolean, default: false },
})

const router = useRouter()

// Local state (optimistic) — keeps working even if list/detail use different post objects
const localLiked = ref(!!props.post?.is_liked)
const localLikesCount = ref(Number(props.post?.likes_count || 0))
const showShareTip = ref(false)

watch(
  () => props.post?.is_liked,
  (v) => {
    localLiked.value = !!v
  }
)

watch(
  () => props.post?.likes_count,
  (v) => {
    const n = Number(v)
    if (!Number.isNaN(n)) localLikesCount.value = n
  }
)

function handleComment() {
  if (props.isDetail) {
    document.getElementById('comments')?.scrollIntoView({ behavior: 'smooth' })
  } else {
    router.push({ path: `/posts/${props.post.id}`, hash: '#comments' })
  }
}

async function handleShare() {
  const url = `${window.location.origin}/posts/${props.post.id}`
  try {
    await navigator.clipboard.writeText(url)
    showShareTip.value = true
    setTimeout(() => (showShareTip.value = false), 2000)
  } catch (err) {
    alert('复制失败，请手动复制浏览器地址')
  }
}

async function handleLike() {
  const originalState = localLiked.value

  localLiked.value = !localLiked.value
  localLikesCount.value += localLiked.value ? 1 : -1

  try {
    const { data } = await api.post(`/api/posts/${props.post.id}/like/`)
    if (typeof data?.liked === 'boolean') localLiked.value = !!data.liked
    if (typeof data?.likes_count === 'number') localLikesCount.value = data.likes_count
  } catch (e) {
    localLiked.value = originalState
    localLikesCount.value += localLiked.value ? 1 : -1
    console.error('点赞失败', e)
  }
}
</script>

<template>
  <div class="action-bar" :class="{ 'detail-mode': isDetail }">
    <div class="action-item comment" @click.stop="handleComment">
      <div class="icon-circle">
        <svg viewBox="0 0 24 24" class="ico">
          <path
            d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.295c-4.42 0-8.005-3.58-8.005-8z"
          ></path>
        </svg>
      </div>
      <span class="count">{{ post.comments_count || 0 }}</span>
    </div>

    <div class="action-item repost" @click.stop="handleShare">
      <div class="icon-circle">
        <svg viewBox="0 0 24 24" class="ico">
          <path
            d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"
          ></path>
        </svg>
      </div>
      <transition name="fade">
        <span v-if="showShareTip" class="share-tip">链接已复制</span>
      </transition>
    </div>

    <div class="action-item like" :class="{ active: localLiked }" @click.stop="handleLike">
      <div class="icon-circle">
        <svg v-if="!localLiked" viewBox="0 0 24 24" class="ico">
          <path
            d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.5 4.798 2.01 1.429-1.51 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"
          ></path>
        </svg>
        <svg v-else viewBox="0 0 24 24" class="ico filled">
          <path
            d="M20.884 13.19c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.5 4.798 2.01 1.429-1.51 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"
          ></path>
        </svg>
      </div>
      <span class="count">{{ localLikesCount }}</span>
    </div>

    <div class="action-item view">
      <div class="icon-circle">
        <svg viewBox="0 0 24 24" class="ico">
          <path d="M8.75 21V3h2v18h-2zM18 21V8.5h2V21h-2zM4 21l.004-10h2L6 21H4zm9.248 0v-7h2v7h-2z"></path>
        </svg>
      </div>
      <span class="count">{{ post.views_count || 0 }}</span>
    </div>
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  justify-content: space-between;
  max-width: 420px;
  margin-top: 8px;
  color: #536471;
  user-select: none;
}

.action-bar.detail-mode {
  max-width: 100%;
  border-top: 1px solid #eff3f4;
  border-bottom: 1px solid #eff3f4;
  padding: 10px 0;
  margin: 20px 0;
  justify-content: space-around;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 0px;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
  color: #536471;
}

.icon-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.ico {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.count {
  font-size: 13px;
  margin-left: 2px;
}

.action-item.comment:hover {
  color: #1d9bf0;
}

.action-item.comment:hover .icon-circle {
  background-color: rgba(29, 155, 240, 0.1);
}

.action-item.repost:hover {
  color: #00ba7c;
}

.action-item.repost:hover .icon-circle {
  background-color: rgba(0, 186, 124, 0.1);
}

.action-item.like:hover {
  color: #f91880;
}

.action-item.like:hover .icon-circle {
  background-color: rgba(249, 24, 128, 0.1);
}

.action-item.like.active {
  color: #f91880;
}

.action-item.like.active .ico {
  fill: #f91880;
}

.action-item.view:hover {
  color: #1d9bf0;
}

.action-item.view:hover .icon-circle {
  background-color: rgba(29, 155, 240, 0.1);
}

.share-tip {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  background: #111827;
  color: #fff;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
