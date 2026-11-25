import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Cổng 5173 khớp VS_CORS_ORIGINS mặc định của vsights-api (CORS + kiểm tra Origin).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
