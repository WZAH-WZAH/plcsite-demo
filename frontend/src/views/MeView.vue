<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const router = useRouter()

const user = ref({})
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const error = ref('')

const avatarInput = ref(null)
const bannerInput = ref(null)

const meInitial = computed(() => {
  const base = String(user.value?.nickname || user.value?.username || '').trim()
  return base ? base.slice(0, 1).toUpperCase() : 'U'
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/users/me/')
    user.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败，请先登录。'
  } finally {
    loading.value = false
  }
}

// 统一保存文本信息
async function saveProfile() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      nickname: user.value.nickname,
      bio: user.value.bio,
      email: user.value.email,
    }
    const { data } = await api.patch('/api/users/me/', payload)
    user.value = data
    await auth.loadMe()
    alert('保存成功')
  } catch (e) {
    const msg = e?.response?.data
    error.value =
      msg?.detail ||
      (Array.isArray(msg?.nickname) ? msg.nickname.join('；') : '') ||
      (Array.isArray(msg?.email) ? msg.email.join('；') : '') ||
      (Array.isArray(msg?.bio) ? msg.bio.join('；') : '') ||
      '保存失败，请检查输入。'
  } finally {
    saving.value = false
  }
}

// 图片上传（头像/头图）
async function handleImageUpload(event, type) {
  const file = event?.target?.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''

  const formData = new FormData()
  formData.append(type, file)

  try {
    const { data } = await api.patch('/api/users/me/', formData)
    user.value = data
    await auth.loadMe()
    alert((type === 'avatar' ? '头像' : '头图') + '更新成功')
  } catch (e) {
    error.value = e?.response?.data?.detail || '图片上传失败'
  } finally {
    uploading.value = false
    if (event?.target) event.target.value = ''
  }
}

function handleLogout() {
  if (!confirm('确定要退出登录吗？')) return
  auth.logout()
  router.push('/login')
}

function backToProfile() {
  const pid = String(user.value?.pid || auth.state.me?.pid || '').trim()
  if (!pid) return
  router.push(`/u/${pid}`)
}

onMounted(load)
</script>

<template>
  <div class="settings-page">
    <div class="settings-container">
      <div class="settings-header">
        <h2>账号设置</h2>
        <button class="btn btn-ghost" type="button" @click="backToProfile">返回个人主页 ›</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="loading" class="muted">加载中...</div>

      <div v-else class="settings-form">
        <div class="form-section">
          <h3>形象设置</h3>
          <div class="visual-edit">
            <div class="avatar-edit" @click="avatarInput?.click()">
              <img v-if="user.avatar_url" :src="user.avatar_url" alt="avatar" />
              <div v-else class="avatar-fallback">{{ meInitial }}</div>
              <div class="mask">修改头像</div>
              <input
                type="file"
                ref="avatarInput"
                hidden
                accept="image/*"
                @change="(e) => handleImageUpload(e, 'avatar')"
              />
            </div>

            <div
              class="banner-edit"
              :style="{ backgroundImage: user.banner_url ? `url(${user.banner_url})` : '' }"
              @click="bannerInput?.click()"
            >
              <div class="banner-mask">点击修改个人空间头图</div>
              <input
                type="file"
                ref="bannerInput"
                hidden
                accept="image/*"
                @change="(e) => handleImageUpload(e, 'banner')"
              />
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>基本信息</h3>

          <div class="form-group">
            <label>用户ID (PID)</label>
            <div class="static-val">{{ user.pid }}</div>
          </div>

          <div class="form-group">
            <label>登录用户名</label>
            <div class="static-val">{{ user.username }} <span class="badge">不可修改</span></div>
          </div>

          <div class="form-group">
            <label>昵称</label>
            <input v-model="user.nickname" class="input" placeholder="设置一个好听的昵称" />
          </div>

          <div class="form-group">
            <label>个性签名</label>
            <textarea v-model="user.bio" class="input textarea" placeholder="介绍一下自己..." rows="3"></textarea>
          </div>

          <div class="form-group">
            <label>邮箱</label>
            <input v-model="user.email" class="input" placeholder="example@email.com" />
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" type="button" :disabled="saving || uploading" @click="saveProfile">
            {{ saving ? '保存中...' : '保存更改' }}
          </button>

          <div class="danger-zone">
            <button class="btn btn-danger" type="button" @click="handleLogout">退出登录</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  background: #f6f7f8;
  min-height: 100vh;
  padding: 40px 20px;
}

.settings-container {
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  padding: 40px;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding-bottom: 20px;
  margin-bottom: 30px;
}

.settings-header h2 {
  margin: 0;
  font-size: 24px;
}

.form-section {
  margin-bottom: 40px;
}

.form-section h3 {
  font-size: 16px;
  margin-bottom: 20px;
  color: #111827;
}

.error {
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  border-radius: 8px;
  color: #991b1b;
}

/* 形象编辑 */
.visual-edit {
  display: flex;
  gap: 20px;
  align-items: center;
}

.avatar-edit {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
  border: 1px solid #eee;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-edit img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  font-weight: 800;
  color: #111827;
}

.mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 12px;
}

.avatar-edit:hover .mask {
  opacity: 1;
}

.banner-edit {
  flex: 1;
  height: 80px;
  border-radius: 8px;
  background-color: #f1f2f3;
  background-size: cover;
  background-position: center;
  position: relative;
  cursor: pointer;
  overflow: hidden;
}

.banner-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 13px;
  font-weight: 500;
}

.banner-edit:hover .banner-mask {
  opacity: 1;
}

/* 表单项 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #374151;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.input:focus {
  border-color: #00aeec;
  outline: none;
}

.textarea {
  resize: vertical;
}

.static-val {
  font-size: 14px;
  color: #6b7280;
  padding: 10px 0;
}

.badge {
  background: #f3f4f6;
  color: #9ca3af;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 8px;
}

/* 按钮 */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.btn {
  padding: 10px 24px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: #00aeec;
  color: #fff;
}

.btn-primary:hover {
  background: #009cd6;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: #00aeec;
  padding: 0;
}

.btn-ghost:hover {
  text-decoration: underline;
}

.btn-danger {
  background: #fee2e2;
  color: #ef4444;
}

.btn-danger:hover {
  background: #fecaca;
}
</style>
