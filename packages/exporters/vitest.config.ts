import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@oh-my-class/renderer': path.resolve(__dirname, '../renderer/src/renderer.ts'),
      '@oh-my-class/renderer/renderer.js': path.resolve(__dirname, '../renderer/src/renderer.ts'),
    },
  },
})
