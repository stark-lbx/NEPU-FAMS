// src/shims-jquery.d.ts
// 声明 window 上的 jQuery 全局（Luckysheet UMD 内部直接访问）
interface Window {
  $: any;
  jQuery: any;
  luckysheet: any;
}
