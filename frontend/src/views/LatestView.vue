<script setup>
  import { ref, onMounted } from 'vue'
  import { apiGet, unwrapList } from '../api'
  import TimelineItem from '../components/TimelineItem.vue' // 引入上面的组件
  
  const posts = ref([])
  const loading = ref(true)
  
  onMounted(async () => {
    try {
      const { data } = await apiGet('/api/posts/feed/latest/', { __skipAuth: true })
      posts.value = unwrapList(data)
    } finally {
      loading.value = false
    }
  })
  </script>
  
  <template>
    <div style="background-color: #ffffff; min-height: 100vh;">
      <div class="timeline-wrapper">
        
        <div class="timeline-header">
          <h2>最新动态</h2>
        </div>
  
        <div v-if="loading" style="padding: 20px; text-align: center; color: #6b7280;">
          正在加载动态...
        </div>
        
        <div v-else class="timeline-feed">
          <TimelineItem 
            v-for="p in posts" 
            :key="p.id" 
            :post="p" 
          />
        </div>
  
        <div v-if="!loading && posts.length === 0" style="padding: 40px; text-align: center; color: #6b7280;">
          暂无最新内容
        </div>
  
      </div>
    </div>
  </template>
  
  <style scoped>
  /* 模拟 X 的中间栏宽度 */
  .timeline-wrapper {
    max-width: 600px; /* 经典推特宽度 */
    margin: 0 auto;   /* 居中 */
    border-left: 1px solid #e5e7eb;
    border-right: 1px solid #e5e7eb;
    min-height: 100vh;
  }
  
  .timeline-header {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(255, 255, 255, 0.85); /* 毛玻璃背景 */
    backdrop-filter: blur(12px);
    padding: 0 16px;
    height: 53px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid #e5e7eb;
    cursor: pointer;
  }
  
  .timeline-header h2 {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    margin: 0;
  }
  </style>