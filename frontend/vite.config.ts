import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxyTarget = process.env.VITE_DEV_PROXY_API_TARGET ?? 'http://127.0.0.1:8899'
const proxiedPaths = ['/.well-known', '/api', '/docs', '/health', '/mcp', '/openapi.json', '/redoc']

const proxy = Object.fromEntries(
  proxiedPaths.map((path) => [
    path,
    {
      target: apiProxyTarget,
      changeOrigin: false,
    },
  ]),
)

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5188,
    proxy,
  },
  preview: {
    host: '0.0.0.0',
    port: 5188,
    proxy,
  },
})
