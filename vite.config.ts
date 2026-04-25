import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const gitCommit = process.env.VITE_GIT_COMMIT || process.env.CF_PAGES_COMMIT_SHA?.slice(0, 7) || 'local';
const buildTime = process.env.VITE_BUILD_TIME || new Date().toISOString();

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {},
  envPrefix: ['VITE_', 'CF_'],
  build: { outDir: 'site', emptyOutDir: false },
});
