// Shared image upload guards for cover image + editor inserts.
// Keep this tiny and dependency-free; backend will still re-encode/compress.

export const MAX_IMAGE_BYTES = 20 * 1024 * 1024

export function formatMiB(bytes) {
  const n = Number(bytes) || 0
  return (n / 1024 / 1024).toFixed(1)
}

export function validateSingleImageFile(file) {
  if (!file) return { ok: false, message: '未选择图片。' }
  const size = Number(file.size) || 0
  if (size <= 0) return { ok: false, message: '图片为空文件。' }
  if (size > MAX_IMAGE_BYTES) {
    return {
      ok: false,
      message: `图片过大：单张不超过20MB（当前约 ${formatMiB(size)}MB）`,
    }
  }
  return { ok: true, message: '' }
}
