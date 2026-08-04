import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
// import tsconfigPaths from "vite-tsconfig-paths";
// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {tsconfigPaths: true},
  server: {
    proxy: {
      '/api': {
        target: 'http://server:5000',
        changeOrigin: true,
      },
      '/auth.opensky-network.org': {
        target: 'https://auth.opensky-network.org',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/auth\.opensky-network\.org/, ''),
      },
      '/opensky-network.org': {
        target: 'https://opensky-network.org',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/opensky-network\.org/, ''),
      },
    },
  },
})
