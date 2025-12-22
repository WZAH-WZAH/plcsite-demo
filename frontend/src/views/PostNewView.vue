<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, apiGet, unwrapList } from '../api'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { sanitizeHtml } from '../sanitize'
import { validateSingleImageFile } from '../imageUpload'
import { formatApiError } from '../errorFormat'

const router = useRouter()

const boards = ref([])
const boardId = ref('')
const title = ref('')
const body = ref('')
const coverFile = ref(null)
const coverPreview = ref('')
const coverDragOver = ref(false)
const editorDragOver = ref(false)
const loading = ref(false)
const error = ref('')

const attachResource = ref(false)
const linkTypes = ref({
  tg: false,
  baidu: false,
  quark: false,
  other: false,
})
const linkUrls = ref({
  tg: '',
  baidu: '',
  quark: '',
  other: '',
})

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

function normalizeImageMarkdown(text) {
  // Some insert paths (e.g. multi-select upload) may end up putting multiple images
  // on the same line. In practice this can make preview rendering flaky.
  // Normalize to: each image starts on a new paragraph.
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
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，当前已超出（${n} 张）。请删除多余图片后再提交。`)
    return false
  }
  return true
}

async function loadBoards() {
  const { data } = await apiGet('/api/boards/', { __skipAuth: true }, 8000)
  boards.value = unwrapList(data)
  if (!boardId.value && boards.value.length) boardId.value = String(boards.value[0].id)
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
  if (coverPreview.value) {
    URL.revokeObjectURL(coverPreview.value)
    coverPreview.value = ''
  }
  if (coverFile.value) {
    coverPreview.value = URL.createObjectURL(coverFile.value)
  }
}

function onCoverDragOver(e) {
  // Always prevent default to avoid the browser opening the dropped file.
  e?.preventDefault?.()
  coverDragOver.value = true
}

function onCoverDragLeave() {
  coverDragOver.value = false
}

function onCoverDrop(e) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  coverDragOver.value = false
  const files = Array.from(e?.dataTransfer?.files || [])
  const img = files.find((f) => (f?.type || '').toLowerCase().startsWith('image/'))
  if (!img) return
  setCoverFile(img)
}

function clearCover() {
  coverFile.value = null
  if (coverPreview.value) {
    URL.revokeObjectURL(coverPreview.value)
    coverPreview.value = ''
  }
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

    // MdEditor inserts markdown at cursor; normalize right after it updates v-model.
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
  const next = normalizeImageMarkdown((body.value || '').trimEnd() + `\n\n${chunks}\n`)
  if (!ensureBodyImageLimit(next)) return
  body.value = next

  if (skipped > 0) {
    window.alert(`正文图片最多 ${MAX_BODY_IMAGES} 张，已超出 ${skipped} 张未插入。`)
  }
}

async function onEditorDrop(e) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  editorDragOver.value = false
  const files = Array.from(e?.dataTransfer?.files || []).filter((f) =>
    (f?.type || '').toLowerCase().startsWith('image/')
  )
  if (files.length === 0) return

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
  e?.preventDefault?.()
  editorDragOver.value = true
}

function onEditorDragLeave() {
  editorDragOver.value = false
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    body.value = normalizeImageMarkdown(body.value)
    if (!ensureBodyImageLimit(body.value)) return

    const form = new FormData()
    form.append('board', String(Number(boardId.value)))
    form.append('title', title.value.trim())
    form.append('body', body.value)
    if (coverFile.value) {
      form.append('cover_image', coverFile.value)
    }

    if (attachResource.value) {
      const selected = Object.entries(linkTypes.value).filter(([, v]) => v)
      const links = []
      for (const [k] of selected) {
        const url = (linkUrls.value[k] || '').trim()
        if (!url) {
          error.value = '已选择附加资源，但有链接未填写。'
          return
        }
        links.push({ link_type: k, url })
      }
      if (links.length === 0) {
        error.value = '请选择至少一个资源链接类型。'
        return
      }
      form.append('resource_links', JSON.stringify(links))
    }

    const { data } = await api.post('/api/posts/', form)
    await router.push(`/posts/${data.id}`)
  } catch (e) {
    error.value = formatApiError(e, '发布失败。')
  } finally {
    loading.value = false
  }
}

onMounted(loadBoards)
</script>

<template>
  <div class="card stack">
    <div class="row" style="justify-content: space-between">
      <h2 style="margin: 0">发帖</h2>
      <RouterLink class="btn" to="/">返回</RouterLink>
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
          <div class="muted" style="font-size: 12px">可选：用于帖子头部展示</div>
        </div>
        <button v-if="coverFile" class="btn" type="button" @click="clearCover">移除</button>
      </div>

      <div class="stack" style="gap: 10px; margin-top: 10px">
        <div
          class="card"
          style="padding: 10px"
          @dragenter.prevent.stop="onCoverDragOver"
          @dragover.prevent.stop="onCoverDragOver"
          @dragleave="onCoverDragLeave"
          @drop.prevent.stop="onCoverDrop"
        >
          <div class="muted" style="font-size: 12px; margin-bottom: 6px">
            可点击选择或拖拽图片到此处（单张≤20MB）
            <span v-if="coverDragOver">（松开即可上传）</span>
          </div>
          <input type="file" accept="image/*" @change="onPickCover" />
        </div>
        <img v-if="coverPreview" :src="coverPreview" alt="cover" style="max-width: 100%; border-radius: 10px" />
      </div>
    </div>

    <div
      class="stack"
      style="gap: 6px"
      @dragenter.prevent.stop="onEditorDragOver"
      @dragover.prevent.stop="onEditorDragOver"
      @dragleave="onEditorDragLeave"
      @drop.prevent.stop="onEditorDrop"
    >
      <div>正文</div>
      <div v-if="editorDragOver" class="muted" style="font-size: 12px">松开鼠标即可插入图片（单张≤20MB）</div>
      <MdEditor
        v-model="body"
        :sanitize="sanitizeHtml"
        :defToolbars="defToolbars"
        :toolbars="[
          'boldStrict',
          'italicStrict',
          'underlineStrict',
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

    <div class="card" style="padding: 12px">
      <label class="row" style="gap: 8px">
        <input type="checkbox" v-model="attachResource" style="width: auto" />
        <span>附加资源文件</span>
      </label>

      <div v-if="attachResource" class="stack" style="gap: 10px; margin-top: 10px">
        <div class="row" style="gap: 12px">
          <label class="row" style="gap: 6px">
            <input type="checkbox" v-model="linkTypes.tg" style="width: auto" />
            <span>TG链接</span>
          </label>
          <label class="row" style="gap: 6px">
            <input type="checkbox" v-model="linkTypes.baidu" style="width: auto" />
            <span>百度网盘</span>
          </label>
          <label class="row" style="gap: 6px">
            <input type="checkbox" v-model="linkTypes.quark" style="width: auto" />
            <span>夸克网盘</span>
          </label>
          <label class="row" style="gap: 6px">
            <input type="checkbox" v-model="linkTypes.other" style="width: auto" />
            <span>其他网盘</span>
          </label>
        </div>

        <label v-if="linkTypes.tg" class="stack" style="gap: 6px">
          <div>添加TG链接</div>
          <input v-model="linkUrls.tg" placeholder="https://t.me/..." />
        </label>
        <label v-if="linkTypes.baidu" class="stack" style="gap: 6px">
          <div>添加百度网盘链接</div>
          <input v-model="linkUrls.baidu" placeholder="https://pan.baidu.com/..." />
        </label>
        <label v-if="linkTypes.quark" class="stack" style="gap: 6px">
          <div>添加夸克网盘链接</div>
          <input v-model="linkUrls.quark" placeholder="https://pan.quark.cn/..." />
        </label>
        <label v-if="linkTypes.other" class="stack" style="gap: 6px">
          <div>添加其他网盘链接</div>
          <input v-model="linkUrls.other" placeholder="https://..." />
        </label>

        <div class="muted" style="font-size: 12px">
          提示：附加资源会走同一套审核与下载配额逻辑。
        </div>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: #fecaca; background: #fff1f2">{{ error }}</div>

    <button class="btn btn-primary" :disabled="loading" @click="submit">
      {{ loading ? '提交中…' : '提交' }}
    </button>

    <div class="muted">普通用户发帖默认进入“待审核”。管理员发帖可直接发布。</div>
  </div>
</template>
