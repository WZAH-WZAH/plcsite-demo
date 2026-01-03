const DT_FMT = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
})

export function fmtDateTime(input) {
  if (!input) return ''
  const d = input instanceof Date ? input : new Date(input)
  if (!(d instanceof Date) || Number.isNaN(d.getTime())) return ''

  // Build a stable format: YYYY-MM-DD HH:mm:ss
  const parts = DT_FMT.formatToParts(d)
  const map = {}
  for (const p of parts) {
    if (p.type === 'literal') continue
    map[p.type] = p.value
  }
  const yyyy = map.year || ''
  const mm = map.month || ''
  const dd = map.day || ''
  const HH = map.hour || ''
  const MM = map.minute || ''
  const SS = map.second || ''

  if (!yyyy || !mm || !dd) return ''
  if (!HH || !MM || !SS) return `${yyyy}-${mm}-${dd}`
  return `${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}`
}
