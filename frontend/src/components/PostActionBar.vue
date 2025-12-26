<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const props = defineProps({
  post: { type: Object, required: true },
  isDetail: { type: Boolean, default: false },
})

const router = useRouter()
const localLiked = ref(props.post.is_liked || false)
const localLikesCount = ref(props.post.likes_count || 0)
// 本地分享计数 (后端暂无字段，纯前端交互反馈)
const localShareCount = ref(0)
const showShareTip = ref(false)

// 1. 评论跳转
function handleComment() {
  if (props.isDetail) {
    document.getElementById('comments')?.scrollIntoView({ behavior: 'smooth' })
  } else {
    router.push({ path: `/posts/${props.post.id}`, hash: '#comments' })
  }
}

// 2. 转发/分享 (点击计数+1)
async function handleShare() {
  const url = `${window.location.origin}/posts/${props.post.id}`
  try {
    await navigator.clipboard.writeText(url)
    localShareCount.value++
    showShareTip.value = true
    setTimeout(() => (showShareTip.value = false), 2000)
  } catch (err) {
    alert('复制失败，请手动复制浏览器地址')
  }
}

// 3. 点赞
async function handleLike() {
  const originalState = localLiked.value
  localLiked.value = !localLiked.value
  localLikesCount.value += localLiked.value ? 1 : -1

  try {
    await api.post(`/api/posts/${props.post.id}/like/`)
  } catch (e) {
    localLiked.value = originalState
    localLikesCount.value += localLiked.value ? 1 : -1
  }
}
</script>

<template>
  <div class="action-bar" :class="{ 'detail-mode': isDetail }">
    <div class="action-item comment" @click.stop="handleComment">
      <div class="icon-circle">
        <svg
          viewBox="0 0 24 24"
          class="ico"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
          ></path>
        </svg>
      </div>
      <span class="count">{{ post.comments_count || 0 }}</span>
    </div>

    <div class="action-item repost" @click.stop="handleShare">
      <div class="icon-circle">
        <svg
          viewBox="0 0 24 24"
          class="ico"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M17 1l4 4-4 4"></path>
          <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
          <path d="M7 23l-4-4 4-4"></path>
          <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
        </svg>
      </div>
      <span class="count">{{ localShareCount > 0 ? localShareCount : '' }}</span>
      <transition name="fade">
        <span v-if="showShareTip" class="share-tip">链接已复制</span>
      </transition>
    </div>

    <div class="action-item like" :class="{ active: localLiked }" @click.stop="handleLike">
      <div class="icon-circle">
        <svg
          v-if="!localLiked"
          viewBox="0 0 24 24"
          class="ico"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
          ></path>
        </svg>
        <svg v-else viewBox="0 0 24 24" class="ico filled">
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
          ></path>
        </svg>
      </div>
      <span class="count">{{ localLikesCount }}</span>
    </div>

    <div class="action-item view">
      <div class="icon-circle">
        <svg
          viewBox="0 0 24 24"
          class="ico"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
          <circle cx="12" cy="12" r="3"></circle>
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
  color: #6b7280;
  font-family: system-ui, -apple-system, sans-serif;
  user-select: none;
}

.action-bar.detail-mode {
  max-width: 100%;
  border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 0;
  margin: 30px 0;
  justify-content: space-around;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.action-item:hover {
  color: #111827;
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
}

.ico.filled {
  fill: #f91880;
  stroke: none;
}

.count {
  font-size: 13px;
  min-width: 16px;
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
