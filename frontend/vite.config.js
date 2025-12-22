import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Windows 上常见坑：默认 localhost 可能只绑定到 IPv6 (::1)，
    // 导致你用 http://127.0.0.1:5173 访问时“无法连接/一直加载中”。
    // 这里强制绑定到 IPv4 回环，确保 127.0.0.1 可用。
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      // 前端通过 /api 访问后端，开发时由 Vite 转发到 Django
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      // 用户上传的图片
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
