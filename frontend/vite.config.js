import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

// Docker dev: PROXY_TARGET=http://backend-api:8082 (docker-compose에서 설정)
// 로컬 dev: 기본값 http://localhost:8082
const proxyTarget = process.env.PROXY_TARGET || 'http://localhost:8082';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'images/apple-touch-icon.png'],
      manifest: {
        name: '아델리에',
        short_name: '아델리에',
        description: 'AI 기반 금융 학습 플랫폼 - 역사는 반복된다',
        theme_color: '#FF6B00',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        lang: 'ko',
        id: '/',
        categories: ['finance', 'education'],
        shortcuts: [
          {
            name: '오늘의 키워드',
            short_name: '키워드',
            url: '/',
            icons: [{ src: '/images/icon-192.png', sizes: '192x192' }],
          },
        ],
        icons: [
          {
            src: '/images/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/images/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/images/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        globPatterns: ['**/*.html'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          // 정적 에셋 — StaleWhileRevalidate (Vite content hash → stale 불가)
          {
            urlPattern: /\/assets\/.+\.(js|css)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-assets',
              expiration: { maxEntries: 60, maxAgeSeconds: 7 * 24 * 60 * 60 },
            },
          },
          // SSE 튜터 채팅 — 캐싱 불가
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/tutor\/.*/i,
            handler: 'NetworkOnly',
          },
          // 모든 API — NetworkFirst (항상 최신, 오프라인 폴백용)
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 5 * 60 },
            },
          },
        ],
      },
    }),
  ],
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
        target: proxyTarget,
        changeOrigin: true,
      },
      // 인증 엔드포인트 (/api/auth/* → FastAPI)
      '/api/auth': {
        target: proxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/auth/, '/api/v1/auth'),
      },
      '/api/health': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          plotly: ['react-plotly.js', 'plotly.js-basic-dist-min'],
          'framer-motion': ['framer-motion'],
          chartjs: ['chart.js', 'react-chartjs-2'],
        },
      },
    },
  },
});
