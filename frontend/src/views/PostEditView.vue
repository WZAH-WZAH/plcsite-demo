<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiGet, unwrapList } from '../api'
import { auth } from '../auth'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { sanitizeHtml } from '../sanitize'
import { validateSingleImageFile } from '../imageUpload'
import { formatApiError } from '../errorFormat'

const route = useRoute()
const router = useRouter()

const postId = computed(() => Number(route.params.id))

const boards = ref([])
const boardId = ref('')
const title = ref('')
const body = ref('')

const existingCoverUrl = ref('')
const removeCover = ref(false)

const coverFile = ref(null)
const coverPreview = ref('')

const coverDragOver = ref(false)
const editorDragOver = ref(false)

const loading = ref(false)
const error = ref('')

function normalizeImageMarkdown(text) {
  return String(text || '').replace(/\)\s*(!\[[^\]]*\]\()/g, ')\n\n$1')
}

const MAX_BODY_IMAGES = 10

function countBodyImages(text) {
  const s = String(text || '')
  const md = s.match(/!\[[^\]]*\]\([^\)]+\)/g) || []
  const html = s.match(/<img\b[^>]*>/gi) || []
  return md.length + html.length
}

function ensureBodyImageLimit(nextText) {
  const n = countBodyImages(nextText)
  if (n > MAX_BODY_IMAGES) {
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，当前已超出（${n} 张）。请删除多余图片后再保存。`)
    return false
  }
  return true
}

const defToolbars = {
  linkStrict: {
    title: '链接',
    icon: '🔗',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = (selectedText || '').trim()
        const label = t || '链接文字'
        const url = window.prompt('输入链接地址', 'https://')
        if (!url) return { text: '', selected: '' }
        return {
          text: `[${label}](${url})`,
          selected: label,
        }
      })
    },
  },
  boldStrict: {
    title: '加粗',
    icon: 'B',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = (selectedText || '').trim()
        const label = t || '加粗文字'
        return {
          text: `**${label}**`,
          selected: label,
        }
      })
    },
  },
  underlineStrict: {
    title: '下划线',
    icon: 'U',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = (selectedText || '').trim()
        const label = t || '下划线文字'
        return {
          text: `<u>${label}</u>`,
          selected: label,
        }
      })
    },
  },
  italicStrict: {
    title: '斜体',
    icon: 'I',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = (selectedText || '').trim()
        const label = t || '斜体文字'
        return {
          text: `*${label}*`,
          selected: label,
        }
      })
    },
  },
  strikeStrict: {
    title: '删除线',
    icon: 'S',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = (selectedText || '').trim()
        const label = t || '删除线文字'
        return {
          text: `~~${label}~~`,
          selected: label,
        }
      })
    },
  },
  spoiler: {
    title: '文字遮罩',
    icon: 'S',
    action: (editor) => {
      editor?.insert?.((selectedText) => {
        const t = selectedText || '遮罩文字'
        return {
          text: `<span class="spoiler">${t}</span>`,
          selected: t,
        }
      })
    },
  },
}

async function loadBoards() {
  const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
  boards.value = unwrapList(data)
}

async function loadPost() {
  const { data } = await api.get(`/api/posts/${postId.value}/`)
  boardId.value = String(data.board)
  title.value = data.title || ''
  body.value = data.body || ''
  existingCoverUrl.value = data.cover_image_url || ''
  removeCover.value = false
}

function onPickCover(e) {
  const f = e?.target?.files?.[0]
  setCoverFile(f || null, e?.target)
}

function setCoverFile(f, inputEl = null) {
  if (f) {
    const v = validateSingleImageFile(f)
    if (!v.ok) {
      error.value = v.message
      coverFile.value = null
      if (inputEl) inputEl.value = ''
      return
    }
  }

  coverFile.value = f || null
  removeCover.value = false
  if (coverPreview.value) {
    URL.revokeObjectURL(coverPreview.value)
    coverPreview.value = ''
  }
  if (coverFile.value) {
    coverPreview.value = URL.createObjectURL(coverFile.value)
  }
}

function onCoverDragOver(e) {
  if (e?.dataTransfer?.types?.includes?.('Files')) {
    e.preventDefault()
    coverDragOver.value = true
  }
}

function onCoverDragLeave() {
  coverDragOver.value = false
}

function onCoverDrop(e) {
  coverDragOver.value = false
  const files = Array.from(e?.dataTransfer?.files || [])
  const img = files.find((f) => (f?.type || '').toLowerCase().startsWith('image/'))
  if (!img) return
  e.preventDefault()
  removeCover.value = false
  setCoverFile(img)
}

function clearNewCover() {
  coverFile.value = null
  if (coverPreview.value) {
    URL.revokeObjectURL(coverPreview.value)
    coverPreview.value = ''
  }
}

function markRemoveCover() {
  clearNewCover()
  removeCover.value = true
}

async function onUploadImg(files, callback) {
  try {
    const currentCount = countBodyImages(body.value)
    const remaining = MAX_BODY_IMAGES - currentCount
    if (remaining <= 0) {
      window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已达到上限。`)
      callback([])
      return
    }

    const urls = []
    const selectedFiles = Array.from(files || []).slice(0, remaining)
    const skipped = Math.max(0, (files?.length || 0) - selectedFiles.length)
    for (const f of selectedFiles) {
      const v = validateSingleImageFile(f)
      if (!v.ok) {
        error.value = v.message
        continue
      }
      const form = new FormData()
      form.append('image', f)
      const { data } = await api.post('/api/posts/images/upload/', form)
      if (data?.url) urls.push(data.url)
    }
    callback(urls)

    if (skipped > 0) {
      window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已超出 ${skipped} 张未插入。`)
    }

    setTimeout(() => {
      body.value = normalizeImageMarkdown(body.value)
    }, 0)
  } catch (e) {
    error.value = e?.response?.data?.detail || '图片上传失败。'
    callback([])
  }
}

async function uploadImages(files) {
  const urls = []
  for (const f of files) {
    const v = validateSingleImageFile(f)
    if (!v.ok) {
      error.value = v.message
      continue
    }
    const form = new FormData()
    form.append('image', f)
    const { data } = await api.post('/api/posts/images/upload/', form)
    if (data?.url) urls.push(data.url)
  }
  return urls
}

function insertImageUrlsToBody(urls) {
  if (!urls || urls.length === 0) return
  const currentCount = countBodyImages(body.value)
  const remaining = MAX_BODY_IMAGES - currentCount
  if (remaining <= 0) {
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已达到上限。`)
    return
  }

  const usable = urls.slice(0, remaining)
  const skipped = Math.max(0, urls.length - usable.length)
  const chunks = usable.map((u) => `![](${u})`).join('\n\n')
  const next = (body.value || '').trimEnd() + `\n\n${chunks}\n`
  if (!ensureBodyImageLimit(next)) return
  body.value = next

  if (skipped > 0) {
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已超出 ${skipped} 张未插入。`)
  }
}

async function onEditorDrop(e) {
  editorDragOver.value = false
  const files = Array.from(e?.dataTransfer?.files || []).filter((f) =>
    (f?.type || '').toLowerCase().startsWith('image/')
  )
  if (files.length === 0) return
  e.preventDefault()

  const currentCount = countBodyImages(body.value)
  const remaining = MAX_BODY_IMAGES - currentCount
  if (remaining <= 0) {
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已达到上限。`)
    return
  }

  const selectedFiles = files.slice(0, remaining)
  const skipped = Math.max(0, files.length - selectedFiles.length)

  try {
    const urls = await uploadImages(selectedFiles)
    insertImageUrlsToBody(urls)

    if (skipped > 0) {
      window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已超出 ${skipped} 张未插入。`)
    }
  } catch (err) {
    error.value = err?.response?.data?.detail || '图片上传失败。'
  }
}

function onEditorDragOver(e) {
  if (e?.dataTransfer?.types?.includes?.('Files')) {
    e.preventDefault()
    editorDragOver.value = true
  }
}

function onEditorDragLeave() {
  editorDragOver.value = false
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (!auth.state.me) {
      error.value = '请先登录。'
      return
    }

    const form = new FormData()
    form.append('board', String(Number(boardId.value)))
    form.append('title', title.value.trim())
    body.value = normalizeImageMarkdown(body.value)
    if (!ensureBodyImageLimit(body.value)) return
    form.append('body', body.value)

    if (coverFile.value) {
      form.append('cover_image', coverFile.value)
    } else if (removeCover.value) {
      form.append('remove_cover_image', 'true')
    }

    await api.patch(`/api/posts/${postId.value}/`, form)
    await router.push(`/posts/${postId.value}`)
  } catch (e) {
    error.value = formatApiError(e, '保存失败。')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await auth.loadMe()
  await loadBoards()
  await loadPost()
})
</script>

<template>
  <div class="card stack">
    <div class="row" style="justify-content: space-between">
      <h2 style="margin: 0">编辑帖子</h2>
      <RouterLink class="btn" :to="`/posts/${postId}`">返回</RouterLink>
    </div>

    <label class="stack" style="gap: 6px">
      <div>板块</div>
      <select v-model="boardId">
        <option v-for="b in boards" :key="b.id" :value="String(b.id)">{{ b.title }}</option>
      </select>
    </label>

    <label class="stack" style="gap: 6px">
      <div>标题</div>
      <input v-model="title" maxlength="200" />
    </label>

    <div class="card" style="padding: 12px">
      <div class="row" style="justify-content: space-between">
        <div>
          <div style="font-weight: 700">首图（头图）</div>
          <div class="muted" style="font-size: 12px">可替换或移除</div>
        </div>
        <div class="row">
          <button v-if="existingCoverUrl && !removeCover" class="btn" type="button" @click="markRemoveCover">移除现有</button>
          <button v-if="coverFile" class="btn" type="button" @click="clearNewCover">取消新图</button>
        </div>
      </div>

      <div class="stack" style="gap: 10px; margin-top: 10px">
        <div
          class="card"
          style="padding: 10px"
          @dragover="onCoverDragOver"
          @dragleave="onCoverDragLeave"
          @drop="onCoverDrop"
        >
          <div class="muted" style="font-size: 12px; margin-bottom: 6px">
            可点击选择或拖拽图片到此处（单张≤20MB）
            <span v-if="coverDragOver">（松开即可上传）</span>
          </div>
          <input type="file" accept="image/*" @change="onPickCover" />
        </div>
        <img v-if="coverPreview" :src="coverPreview" alt="cover" style="max-width: 100%; border-radius: 10px" />
        <img v-else-if="existingCoverUrl && !removeCover" :src="existingCoverUrl" alt="cover" style="max-width: 100%; border-radius: 10px" />
        <div v-else class="muted" style="font-size: 12px">无首图</div>
      </div>
    </div>

    <div
      class="stack"
      style="gap: 6px"
      @dragover="onEditorDragOver"
      @dragleave="onEditorDragLeave"
      @drop="onEditorDrop"
    >
      <div>正文</div>
      <div v-if="editorDragOver" class="muted" style="font-size: 12px">松开鼠标即可插入图片（单张≤20MB）</div>
      <MdEditor
        v-model="body"
        :sanitize="sanitizeHtml"
        :defToolbars="defToolbars"
        :toolbars="[
          'boldStrict',
          'underlineStrict',
          'italicStrict',
          'strikeStrict',
          '-',
          'linkStrict',
          'spoiler',
          'image',
          'table',
          'code',
          'quote',
          'unorderedList',
          'orderedList',
          '-',
          'preview',
          'fullscreen',
        ]"
        @onUploadImg="onUploadImg"
      />
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <button class="btn btn-primary" :disabled="loading" @click="submit">
      {{ loading ? '保存中…' : '保存' }}
    </button>

    <div class="muted" style="font-size: 12px">
      提示：普通用户编辑后会重新进入“待审核”。
    </div>
  </div>
</template>
