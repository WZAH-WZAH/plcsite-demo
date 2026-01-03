function translateMessage(msg) {
  const s = String(msg || '')

  if (s === 'This field may not be blank.') return '不能为空。'
  if (s === 'This field is required.') return '为必填项。'
  if (s === 'Invalid pk "null" - object does not exist.') return '无效的选择。'
  if (s === 'Not allowed.') return '无权限。'
  if (s === 'You do not have permission to perform this action.') return '无权限执行此操作。'
  if (s === 'Authentication credentials were not provided.') return '请先登录。'
  if (s === 'Invalid token.' || s === 'Token is invalid or expired') return '登录已过期，请重新登录。'

  // Common DRF patterns
  let m = s.match(/Ensure this field has no more than (\d+) characters\./)
  if (m) return `不能超过 ${m[1]} 个字符。`

  m = s.match(/Ensure this field has at least (\d+) characters\./)
  if (m) return `不能少于 ${m[1]} 个字符。`

  m = s.match(/Ensure this field has no more than (\d+) elements\./)
  if (m) return `数量不能超过 ${m[1]}。`

  m = s.match(/Ensure this field has at least (\d+) elements\./)
  if (m) return `数量不能少于 ${m[1]}。`

  return s
}

const FIELD_LABELS = {
  title: '标题',
  body: '正文',
  board: '板块',
  cover_image: '头图',
  remove_cover_image: '移除头图',
  resource_links: '资源链接',
  image: '图片',
  username: '用户名',
  password: '密码',
  email: '邮箱',
}

export function formatDrfErrorData(data, fallback = '操作失败。') {
  if (!data) return fallback

  // String body (may be HTML or plain text)
  if (typeof data === 'string') {
    if (data.toLowerCase().includes('<!doctype html')) return fallback
    return data
  }

  // {detail: '...'}
  if (typeof data === 'object' && data.detail) {
    return translateMessage(data.detail)
  }

  if (typeof data !== 'object') return String(data)

  // Field errors: {field: ['msg1', 'msg2'], ...}
  const parts = []
  for (const [field, raw] of Object.entries(data)) {
    if (raw == null) continue

    const label = FIELD_LABELS[field] || field

    const msgs = Array.isArray(raw) ? raw : [raw]
    const rendered = msgs
      .map((m) => translateMessage(m))
      .filter((x) => String(x || '').trim())
      .join('')

    if (!rendered) continue

    // If rendered already ends with punctuation, keep it.
    parts.push(`${label}${rendered.startsWith('：') || rendered.startsWith(':') ? '' : '：'}${rendered}`)
  }

  if (parts.length) return parts.join('；')

  try {
    return JSON.stringify(data)
  } catch {
    return fallback
  }
}

export function formatApiError(e, fallback = '操作失败。') {
  const status = e?.response?.status
  const data = e?.response?.data

  // If backend returned a Django debug/HTML error page.
  if (typeof data === 'string' && data.toLowerCase().includes('<!doctype html')) {
    return `${fallback}（HTTP ${status || 500}）：后端返回了错误页面。`
  }

  return formatDrfErrorData(data, fallback)
}
