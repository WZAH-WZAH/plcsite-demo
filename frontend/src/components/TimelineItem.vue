<script setup>
  import { computed } from 'vue'
  import { useRouter } from 'vue-router'
    
    const props = defineProps({
      post: { type: Object, required: true }
    })

    const router = useRouter()
    
    // 仿 X 的时间格式化 (例如: 2h, 5m, 12月23日)
    function formatXTime(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const now = new Date()
      const diff = (now - date) / 1000 // 秒
      
      if (diff < 60) return '刚刚'
      if (diff < 3600) return Math.floor(diff / 60) + 'm'
      if (diff < 86400) return Math.floor(diff / 3600) + 'h'
      return (date.getMonth() + 1) + '月' + date.getDate() + '日'
    }
    
    const timeDisplay = computed(() => formatXTime(props.post.created_at))

    const displayNickname = computed(() => props.post?.author_nickname || props.post?.author_username || '用户')
    const displayHandle = computed(() => props.post?.author_username || '')

    const excerpt = computed(() => {
      const raw = (props.post?.body || '').toString()
      const normalized = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      const lines = normalized
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)

      const text = lines.join('\n').trim()
      if (!text) return ''
      return text.length > 120 ? text.slice(0, 120) + '…' : text
    })
    </script>
    
    <template>
      <div class="x-item" @click="router.push(`/posts/${post.id}`)">
        <div class="x-avatar-area">
          <div class="x-avatar">
            {{ displayNickname?.[0]?.toUpperCase() || 'U' }}
          </div>
        </div>
    
        <div class="x-content">
          
          <div class="x-header">
            <span class="x-name">{{ displayNickname }}</span>
            <span v-if="displayHandle" class="x-handle">{{ displayHandle }}</span>
            <span class="x-dot">·</span>
            <span class="x-time">{{ timeDisplay }}</span>
          </div>
    
          <div class="x-text">
            <div class="x-title">{{ post.title }}</div>
            <div v-if="excerpt" class="x-excerpt">{{ excerpt }}</div>
            <div v-else class="muted">查看详情...</div>
          </div>
    
          <div v-if="post.cover_image_url" class="x-media" @click.stop="router.push(`/posts/${post.id}`)">
            <img :src="post.cover_image_url" loading="lazy" />
          </div>
    
          <div class="x-actions">
            <div class="x-action-btn comment">
              <i>💬</i> <span>{{ post.comments_count || 0 }}</span>
            </div>
            <div class="x-action-btn repost">
              <i>🔁</i> <span>0</span>
            </div>
            <div class="x-action-btn like">
              <i>🤍</i> <span>{{ post.likes_count || 0 }}</span>
            </div>
            <div class="x-action-btn view">
              <i>📊</i> <span>{{ post.views_count || 0 }}</span>
            </div>
          </div>
    
        </div>
      </div>
    </template>
    
    <style scoped>
    /* 容器：没有圆角，只有底边框，像推特一样 */
    .x-item {
      display: flex;
      padding: 12px 16px;
      border-bottom: 1px solid #e5e7eb;
      cursor: pointer;
      background: #ffffff;
      transition: background-color 0.2s;
    }
    .x-item:hover {
      background-color: #f9fafb;
    }
    
    /* 左侧头像 */
    .x-avatar-area {
      margin-right: 12px;
      flex-shrink: 0;
    }
    .x-avatar {
      width: 40px; height: 40px;
      background: #ffffff;
      border-radius: 50%;
      border: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: #111827;
    }
    
    /* 右侧内容 */
    .x-content {
      flex: 1;
      min-width: 0;
    }
    
    /* 头部信息 */
    .x-header {
      display: flex;
      align-items: baseline;
      font-size: 15px;
      line-height: 20px;
    }
    .x-name {
      font-weight: 700;
      color: #111827;
      margin-right: 4px;
    }
    .x-handle, .x-dot, .x-time {
      color: #6b7280;
      font-size: 15px;
    }
    .x-dot { margin: 0 4px; }
    
    /* 文本 */
    .x-text {
      font-size: 15px;
      line-height: 20px;
      color: #111827;
      margin-top: 2px;
      word-wrap: break-word;
    }

    .x-title {
      font-weight: 700;
      margin-bottom: 4px;
    }

    .x-excerpt {
      color: #111827;
      white-space: pre-line;
    }
    
    /* 媒体图 (圆角大图) */
    .x-media {
      margin-top: 10px;
      border-radius: 16px;
      border: 1px solid #e5e7eb;
      overflow: hidden;
      max-height: 500px;
    }
    .x-media img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    
    /* 底部操作栏 */
    .x-actions {
      display: flex;
      justify-content: space-between;
      margin-top: 12px;
      max-width: 400px; /* 限制宽度，不拉太长 */
    }
    .x-action-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #6b7280;
      font-size: 13px;
      transition: color 0.2s;
    }
    .x-action-btn i { font-style: normal; font-size: 16px; }
    .x-action-btn:hover { color: #111827; }
    </style>