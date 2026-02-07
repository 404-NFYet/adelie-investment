import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  // 프로젝트 루트의 .env 파일을 로드 (VITE_* 환경변수)
  envDir: path.resolve(__dirname, '..'),
  server: {
    host: '0.0.0.0',
    port: 3001,
    strictPort: true,
    open: false,
    // 개발 서버 프록시: CORS 없이 백엔드 API 호출 가능
    proxy: {
      // FastAPI 엔드포인트 (/api/v1/*)
      '/api/v1': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      // Spring Boot 엔드포인트 (/api/auth/*, /api/user/* 등)
      '/api/auth': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/user': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/bookmarks': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/history': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/settings': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/health': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/glossary': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
