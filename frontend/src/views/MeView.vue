<script setup>
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const router = useRouter()

const me = computed(() => auth.state.me)
const user = ref({ id: null, username: '', avatar_url: '', bio: '' })

const fileInput = ref(null)
const uploading = ref(false)
const saving = ref(false)
const error = ref('')

const meInitial = computed(() => {
  const s = (user.value?.username || '').trim()
  return s ? s.slice(0, 1).toUpperCase() : 'U'
})

watchEffect(() => {
  if (!me.value) return
  user.value = {
    id: me.value?.id ?? null,
    username: me.value?.username || '',
    avatar_url: me.value?.avatar_url || '',
    bio: me.value?.bio || '',
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function triggerUpload() {
  fileInput.value?.click?.()
}

async function onFileChange(e) {
  const file = e?.target?.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('avatar', file)
    await api.post('/api/me/avatar/', fd)
    await auth.loadMe()
    user.value.avatar_url = auth.state.me?.avatar_url || user.value.avatar_url
    alert('头像更新成功')
  } catch (e2) {
    const msg = e2?.response?.data?.detail
    const fieldMsg = Array.isArray(e2?.response?.data?.avatar) ? e2.response.data.avatar.join('；') : ''
    error.value = msg || fieldMsg || '上传失败'
  } finally {
    uploading.value = false
    if (e?.target) e.target.value = ''
  }
}

async function saveBio() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.post('/api/me/bio/', { bio: String(user.value.bio || '') })
    await auth.loadMe()
    user.value.bio = data?.bio ?? user.value.bio
    alert('签名已保存')
  } catch (e2) {
    const msg = e2?.response?.data?.detail
    error.value = msg || '保存失败'
  } finally {
    saving.value = false
  }
}

function viewMySpace() {
  if (!user.value.pid) return
  router.push(`/u/${user.value.pid}`)
}
</script>

<template>
  <div class="settings-container">
    <div class="settings-card">
      <h2 class="page-title">账号设置</h2>

      <div v-if="error" class="error">{{ error }}</div>

      <div class="setting-item">
        <div class="label">当前头像</div>
        <div class="content-row">
          <div class="avatar-wrapper" @click="triggerUpload">
            <img v-if="user.avatar_url" :src="user.avatar_url" alt="avatar" />
            <div v-else class="avatar-fallback">{{ meInitial }}</div>
            <div class="avatar-mask">更换</div>
            <input type="file" ref="fileInput" hidden @change="onFileChange" accept="image/*" />
          </div>
          <div class="actions">
            <button class="btn btn-outline" type="button" @click="viewMySpace">查看我的个人主页 ›</button>
            <div class="tip">点击头像可直接更换</div>
          </div>
        </div>
      </div>

      <div class="setting-item">
        <div class="label">昵称</div>
        <div class="static-text">
          {{ user.username }}
        </div>
      </div>

      <div class="setting-item">
        <div class="label">我的签名</div>
        <input class="input" v-model="user.bio" placeholder="介绍一下你自己..." />
      </div>

      <div class="form-footer">
        <button class="btn save-btn" type="button" :disabled="saving || uploading" @click="saveBio">保存更改</button>
        <button class="btn btn-text" type="button" @click="handleLogout" style="color: #ff473d">退出登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  max-width: 700px;
  margin: 40px auto;
}
.settings-card {
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  border: 1px solid #e3e5e7;
}
.page-title {
  font-size: 20px;
  margin-bottom: 30px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e3e5e7;
}

.error {
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  border-radius: 8px;
  color: #991b1b;
}

.setting-item {
  margin-bottom: 30px;
}
.label {
  font-weight: 700;
  margin-bottom: 10px;
  color: #18191c;
}
.content-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  border: 1px solid #f1f2f3;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-fallback {
  font-weight: 800;
  color: #111827;
}
.avatar-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 13px;
}
.avatar-wrapper:hover .avatar-mask {
  opacity: 1;
}

.input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccd0d7;
  border-radius: 4px;
}
.save-btn {
  background: #00aeec;
  border: none;
  padding: 10px 30px;
}
.tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}
.btn-outline {
  background: #fff;
  border: 1px solid #ccd0d7;
  color: #666;
  font-size: 13px;
  padding: 6px 16px;
}
.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 40px;
}
</style>
