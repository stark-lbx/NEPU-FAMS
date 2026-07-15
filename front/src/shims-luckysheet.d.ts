// src/shims-luckysheet.d.ts
// 补齐 ESM 模式下 luckysheet 的类型导出（build 时 external 走 window.luckysheet）
declare module 'luckysheet' {
  const luckysheet: any
  export default luckysheet
}
