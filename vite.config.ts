import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';
  const allowedHostsExtra = (env.VITE_ALLOWED_HOSTS || '').split(',').map(h => h.trim()).filter(Boolean);
  const backendWsTarget = backendTarget.replace(/^http/, 'ws');

  return {
    base: '/cloud-office/',
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 3000,
      // میزبان‌های مجاز dev server؛ برای دامنه/IP دیگر: VITE_ALLOWED_HOSTS=dev.example.com,.example.org
      allowedHosts: ['localhost', '127.0.0.1', ...allowedHostsExtra],
      proxy: {
        '/api': { target: backendTarget, changeOrigin: true },
        '/ws': { target: backendWsTarget, ws: true },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 3000,
    },
  };
});
