import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

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
        skipWaiting: true,
        clientsClaim: true,
        globPatterns: ['**/*.{js,css,html,svg,woff2}'],
        globIgnores: ['**/images/penguin-3d.png', '**/images/icon-512.png', '**/favicon.ico', '**/images/icon-192.png'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
        runtimeCaching: [
          // SSE 튜터 채팅 — 캐싱 불가
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/tutor\/.*/i,
            handler: 'NetworkOnly',
          },
          // 키워드 — 하루 단위 갱신, 빠른 응답 우선
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/keywords\/.*/i,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'keywords-cache',
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 60, // 1시간
              },
            },
          },
          // 역사적 사례/내러티브 — 변경 거의 없음
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/(cases|narrative)\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'cases-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 24 * 60 * 60, // 24시간
              },
            },
          },
          // 나머지 API — 네트워크 우선, 5분 캐시
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 5 * 60, // 5분
              },
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
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      // Spring Boot 엔드포인트 (/api/auth/*)
      '/api/auth': {
        target: 'http://localhost:8083',
        changeOrigin: true,
      },
      '/api/health': {
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
