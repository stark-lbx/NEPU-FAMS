/** 通用格式化工具 */
export function formatMoney(n: number | string | undefined | null): string {
  if (n === undefined || n === null || n === '') return '0.00'
  const v = Number(n)
  if (Number.isNaN(v)) return '0.00'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatDate(d: string | undefined | null, withTime = true): string {
  if (!d) return '-'
  const dt = new Date(d)
  if (Number.isNaN(dt.getTime())) return d
  const pad = (n: number) => String(n).padStart(2, '0')
  const ymd = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
  if (!withTime) return ymd
  return `${ymd} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

export function parseJwtPayload(token: string): Record<string, any> | null {
  try {
    const s = token.split('.')[1]
    if (!s) return null
    const base64 = s.replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const padded = pad ? base64 + '='.repeat(4 - pad) : base64
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}
