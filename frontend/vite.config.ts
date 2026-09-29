import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      ['/api', '/health', '/docs', '/openapi.json'].map((path) => [
        path,
        { target: process.env.API_PROXY_TARGET || 'http://api:8000', changeOrigin: true },
      ]),
    ),
  },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
})
