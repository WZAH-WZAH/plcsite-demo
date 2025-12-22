import DOMPurify from 'dompurify'

let hooksInstalled = false

function installHooksOnce() {
  if (hooksInstalled) return
  hooksInstalled = true

  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (!node || !node.tagName) return

    // Ensure safe external links
    if (node.tagName === 'A') {
      const target = node.getAttribute('target')
      if (target === '_blank') {
        const rel = (node.getAttribute('rel') || '').split(/\s+/).filter(Boolean)
        const set = new Set(rel)
        set.add('noopener')
        set.add('noreferrer')
        node.setAttribute('rel', Array.from(set).join(' '))
      }
    }

    // Keep span class only for spoiler
    if (node.tagName === 'SPAN' && node.hasAttribute('class')) {
      const cls = (node.getAttribute('class') || '')
        .split(/\s+/)
        .filter((c) => c === 'spoiler')
      if (cls.length) node.setAttribute('class', cls.join(' '))
      else node.removeAttribute('class')
    }

    // Keep code classes only for language-*
    if (node.tagName === 'CODE' && node.hasAttribute('class')) {
      const cls = (node.getAttribute('class') || '')
        .split(/\s+/)
        .filter((c) => c.startsWith('language-'))
      if (cls.length) node.setAttribute('class', cls.join(' '))
      else node.removeAttribute('class')
    }
  })
}

const ALLOWED_TAGS = [
  // layout
  'p',
  'br',
  'hr',
  'blockquote',
  'pre',
  'code',
  'span',
  // text
  'strong',
  'b',
  'em',
  'i',
  'u',
  'del',
  's',
  // lists
  'ul',
  'ol',
  'li',
  // headings
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  // links & images
  'a',
  'img',
  // tables (common in md-editor)
  'table',
  'thead',
  'tbody',
  'tr',
  'th',
  'td',
]

// DOMPurify expects ALLOWED_ATTR as a flat list.
// (Per-tag allowlists are handled via hooks / default DOMPurify behavior.)
const ALLOWED_ATTR = [
  // links
  'href',
  'title',
  'target',
  'rel',
  // images
  'src',
  'alt',
  'width',
  'height',
  'loading',
  // formatting helpers
  'class',
  'align',
]

// Allow http(s), mailto/tel, relative paths and anchors. Block javascript:, data:, vbscript: ...
const ALLOWED_URI_REGEXP = /^(?:(?:https?|mailto|tel):|\/|\.\/|#)/i

export function sanitizeHtml(html) {
  installHooksOnce()

  return DOMPurify.sanitize(String(html || ''), {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOWED_URI_REGEXP,
  })
}
