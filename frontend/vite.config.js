import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

export default defineConfig({
  base: '/static/react-dist/',

  plugins: [react()],

  build: {
    outDir: resolve(
      __dirname,
      '../static/react-dist',
    ),

    emptyOutDir: true,
    cssCodeSplit: false,

    rollupOptions: {
      input: resolve(
        __dirname,
        'src/main.jsx',
      ),

      output: {
        entryFileNames:
          'assets/equalizer-react.js',

        chunkFileNames:
          'assets/[name]-[hash].js',

        assetFileNames: (assetInfo) => {
          const fileName =
            assetInfo.name || ''

          if (
            fileName.endsWith('.css')
          ) {
            return (
              'assets/equalizer-react.css'
            )
          }

          return (
            'assets/[name]-[hash][extname]'
          )
        },
      },
    },
  },
})