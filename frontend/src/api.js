import axios from 'axios'

export const api = axios.create({
  baseURL: '/',
  timeout: 15000,
})

// Abortable GET helper (prevents “loading forever”)
// Notes:
// - In some dev setups (proxy/backend mismatch), browser requests can stay pending.
// - Axios' built-in timeout is usually enough, but this adds a hard abort as a safeguard.
// - Use this in UI-critical pages like Home/TopBar.
export async function apiGet(url, config = {}, timeoutMs = 8000) {
  const controller = new AbortController()
  const ms = Math.max(1000, Number(timeoutMs) || 8000)
  let timeoutTimer = null
  const timeoutPromise = new Promise((_, reject) => {
    timeoutTimer = setTimeout(() => {
      try {
        controller.abort()
      } catch {
        // ignore
      }
      const err = new Error(`Request timeout after ${ms}ms`)
      err.code = 'ETIMEDOUT'
      reject(err)
    }, ms)
  })
  try {
    return await Promise.race([
      api.get(url, { ...(config || {}), signal: controller.signal }),
      timeoutPromise,
    ])
  } finally {
    if (timeoutTimer) clearTimeout(timeoutTimer)
  }
}

let refreshPromise = null

function stripAuthHeader(headers) {
  if (!headers) return headers
  // axios may normalize header keys; handle common variants.
  if (headers.Authorization) delete headers.Authorization
  if (headers.authorization) delete headers.authorization
  return headers
}

function shouldRetryWithoutAuth(original) {
  const method = (original?.method || 'get').toLowerCase()
  if (method !== 'get') return false
  const url = String(original?.url || '')
  if (!url.startsWith('/api/')) return false
  // Do not retry auth endpoints or clearly-auth-only endpoints.
  if (url.startsWith('/api/auth/')) return false
  if (url.startsWith('/api/me')) return false
  if (url.startsWith('/api/notifications/')) return false
  return true
}

api.interceptors.request.use((config) => {
  const url = String(config?.url || '')
  const method = String(config?.method || 'get').toLowerCase()

  // Allow callers to explicitly opt-out of auth headers.
  if (config?.__skipAuth) {
    return config
  }

  // Never attach Authorization to auth endpoints.
  if (url.startsWith('/api/auth/')) {
    return config
  }

  // Default behavior: attach token if present.
  // Note: some public endpoints may still work with auth, but a stale/invalid token can cause 401.
  const token = localStorage.getItem('access_token')
  if (token && method) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const status = err?.response?.status
    const original = err?.config

    if (status !== 401 || !original || original.__isRetryRequest || original.__isRetryNoAuth) {
      return Promise.reject(err)
    }

    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (shouldRetryWithoutAuth(original)) {
        original.__isRetryNoAuth = true
        original.__skipAuth = true
        original.headers = stripAuthHeader({ ...(original.headers || {}) })
        return api(original)
      }
      return Promise.reject(err)
    }

    try {
      if (!refreshPromise) {
        refreshPromise = api.post('/api/auth/token/refresh/', { refresh }).then((r) => r.data)
      }
      const data = await refreshPromise
      if (!data?.access) throw new Error('No access token')
      localStorage.setItem('access_token', data.access)
      // SimpleJWT may rotate refresh tokens; persist the new refresh token if returned.
      if (data?.refresh) {
        localStorage.setItem('refresh_token', data.refresh)
      }
      refreshPromise = null

      original.__isRetryRequest = true
      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${data.access}`
      return api(original)
    } catch (e) {
      refreshPromise = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (shouldRetryWithoutAuth(original)) {
        original.__isRetryNoAuth = true
        original.__skipAuth = true
        original.headers = stripAuthHeader({ ...(original.headers || {}) })
        return api(original)
      }
      return Promise.reject(err)
    }
  }
)

export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}
