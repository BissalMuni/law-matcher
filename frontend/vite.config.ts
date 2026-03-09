import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  envDir: '..',  // 루트 폴더의 .env 파일 읽기
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    watch: {
      usePolling: true,  // Docker 환경에서 파일 변경 감지
      interval: 1000,    // 1초마다 체크
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // SSE 스트리밍 지원: 프록시 타임아웃 비활성화
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
  optimizeDeps: {
    include: ['antd', '@ant-design/icons', 'react', 'react-dom', 'react-router-dom'],
  },
})
