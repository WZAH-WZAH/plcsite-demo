import { reactive } from 'vue'
import { api } from './api'

export const auth = {
  state: reactive({
    me: null,
    loading: false,
    error: null,
  }),

  isAuthed() {
    return Boolean(localStorage.getItem('access_token'))
  },

  async login(username, password) {
    this.state.error = null
    const { data } = await api.post('/api/auth/token/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    await this.loadMe()
  },

  async register({ nickname, username, email, password }) {
    this.state.error = null
    await api.post('/api/auth/register/', { nickname, username, email, password })
    // 备注：首次注册后提示用户设置头像（TopBar 会读取该标记并弹窗一次）。
    localStorage.setItem('plc_avatar_prompt', '1')
    await this.login(username, password)
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    this.state.me = null
  },

  async loadMe() {
    if (!this.isAuthed()) {
      this.state.me = null
      return
    }
    this.state.loading = true
    try {
      const { data } = await api.get('/api/me/')
      this.state.me = data
    } catch (e) {
      this.state.me = null
    } finally {
      this.state.loading = false
    }
  },
}
