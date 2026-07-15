import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 协同盘点：Luckysheet
// 注意：jQuery / jquery-mousewheel / luckysheet UMD 全部由 index.html 同步 <script> 加载，
// 此时 window.$ / window.jQuery / window.luckysheet / $.fn.mousewheel 都已经就绪。
// 不要在这里 import 这些包（Vite 会走 package.json#module 解析到有问题的入口）。

import App from './App.vue'
import router from './router'
import './styles/index.scss'

const app = createApp(App)

// 全局注册所有 Element Plus 图标
for (const [k, v] of Object.entries(ElementPlusIconsVue)) {
  app.component(k, v as any)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
