<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const router = useRouter()

const user = ref(auth.state.me ? { ...auth.state.me } : {})
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const error = ref('')

const avatarInput = ref(null)

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
    await auth.loadMe()
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败，请先登录。'
  } finally {
    loading.value = false
  }
}

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
    alert('个人资料已更新')
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

function triggerAvatar() {
  avatarInput.value?.click?.()
}

async function handleAvatarChange(e) {
  const file = e?.target?.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('avatar', file)
    const { data } = await api.patch('/api/users/me/', fd)
    user.value = data
    await auth.loadMe()
    alert('头像更换成功')
  } catch (err) {
    error.value = err?.response?.data?.detail || '图片上传失败'
  } finally {
    uploading.value = false
    if (e?.target) e.target.value = ''
  }
}

function handleLogout() {
  if (!confirm('确定要退出登录吗？')) return
  auth.logout()
  router.push('/login')
}

function viewMyPage() {
  const pid = String(user.value?.pid || auth.state.me?.pid || '').trim()
  if (!pid) return
  router.push(`/u/${pid}`)
}

onMounted(load)
</script>

<template>
  <div class="settings-layout">
    <div class="settings-box">
      <div class="s-header">
        <h2>账号设置</h2>
        <a class="back-link" @click="viewMyPage">返回个人空间 &gt;</a>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="loading" class="loading-txt">加载中...</div>

      <div v-else class="s-form">
        <div class="form-row avatar-row">
          <label>当前头像</label>
          <div class="avatar-edit" @click="triggerAvatar">
            <img v-if="user.avatar_url" :src="user.avatar_url" alt="avatar" />
            <div v-else class="avatar-fallback">{{ meInitial }}</div>
            <div class="edit-mask">{{ uploading ? '上传中...' : '修改' }}</div>
            <input type="file" ref="avatarInput" hidden @change="handleAvatarChange" accept="image/*" />
          </div>
          <div class="avatar-tip">
            支持 jpg, png 格式，大小不超过 20MB<br />
            点击头像即可直接更换
          </div>
        </div>

        <div class="divider"></div>

        <div class="form-row">
          <label>昵称</label>
          <div class="input-wrap">
            <input v-model="user.nickname" type="text" class="bili-input" placeholder="请输入昵称" />
          </div>
        </div>

        <div class="form-row">
          <label>用户名</label>
          <div class="static-text">
            {{ user.username }} <span class="tag">UID: {{ user.pid }}</span>
          </div>
        </div>

        <div class="form-row">
          <label>个性签名</label>
          <div class="input-wrap">
            <textarea v-model="user.bio" class="bili-input area" placeholder="设置您的签名"></textarea>
          </div>
        </div>

        <div class="form-row">
          <label>邮箱</label>
          <div class="input-wrap">
            <input v-model="user.email" type="email" class="bili-input" />
          </div>
        </div>

        <div class="divider"></div>

        <div class="footer-btns">
          <button class="btn-save" type="button" @click="saveProfile" :disabled="saving || uploading">
            {{ saving ? '保存中...' : '保存设置' }}
          </button>

          <button class="btn-logout" type="button" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-layout {
  background: #f4f5f7;
  min-height: 100vh;
  padding-top: 30px;
  padding-left: 16px;
  padding-right: 16px;
}

.settings-box {
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e1e2e5;
  padding: 30px 40px;
}

.s-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e9ef;
  margin-bottom: 30px;
}

.s-header h2 {
  font-size: 20px;
  color: #333;
  margin: 0;
}

.back-link {
  font-size: 14px;
  color: #00aeec;
  cursor: pointer;
}

.back-link:hover {
  text-decoration: underline;
}

.loading-txt {
  color: #6d757a;
  padding: 12px 0;
}

.error {
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  border-radius: 8px;
  color: #991b1b;
}

.form-row {
  display: flex;
  margin-bottom: 24px;
}

.form-row label {
  width: 90px;
  text-align: right;
  margin-right: 20px;
  font-size: 14px;
  color: #222;
  padding-top: 10px;
  font-weight: 700;
}

.avatar-edit {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  border: 1px solid #e5e9ef;
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
  width: 100%;
  height: 100%;
  background: #f1f2f3;
  color: #6d757a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 800;
}

.edit-mask {
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

.avatar-edit:hover .edit-mask {
  opacity: 1;
}

.avatar-tip {
  font-size: 12px;
  color: #99a2aa;
  margin-left: 20px;
  padding-top: 10px;
  line-height: 1.5;
}

.input-wrap {
  flex: 1;
  max-width: 400px;
}

.bili-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  font-size: 14px;
  color: #222;
  outline: none;
  transition: border 0.2s;
}

.bili-input:focus {
  border-color: #00aeec;
}

.area {
  height: 80px;
  resize: vertical;
}

.static-text {
  padding-top: 10px;
  color: #6d757a;
  font-size: 14px;
}

.tag {
  background: #f4f5f7;
  color: #99a2aa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  margin-left: 8px;
}

.divider {
  height: 1px;
  background: #e5e9ef;
  margin: 30px 0;
}

.footer-btns {
  padding-left: 110px;
  display: flex;
  gap: 20px;
}

.btn-save {
  width: 120px;
  height: 36px;
  background: #00aeec;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-save:hover {
  background: #00a1d6;
}

.btn-save:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-logout {
  width: 120px;
  height: 36px;
  background: #ffeded;
  color: #ff5050;
  border: 1px solid #ffcccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-logout:hover {
  background: #ffcccc;
}
</style>
