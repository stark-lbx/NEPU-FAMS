import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: [
      'dayjs',
      'flatpickr',
      'numeral',
      'pako',
    ],
    // jquery / jquery-mousewheel / luckysheet 全部由 index.html 同步 <script> 加载，
    // 不走 Vite 模块解析，避免 package.json#module 解析到问题版本
    exclude: [
      'jquery',
      'jquery-mousewheel',
      'luckysheet',
    ],
  },
  server: {
    port: 5174,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9900',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      // build 时把 luckysheet 当 external，让它走 window.luckysheet
      // jquery 也走 external，因为前端代码 import 不到
      external: ['luckysheet'],
      output: {
        globals: {
          luckysheet: 'luckysheet',
        },
        manualChunks: {
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          echarts: ['echarts'],
        },
      },
    },
  },
})
