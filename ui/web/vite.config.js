import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During `npm run dev` the page runs on :5173 and forwards API calls to FastAPI on :8000.
// After `npm run build`, FastAPI serves the built files itself, so no proxy is needed.
const api = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/documents': api, '/ask': api, '/config': api, '/health': api },
  },
});
