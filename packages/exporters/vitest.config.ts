import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@oh-my-class/renderer': path.resolve(__dirname, '../renderer/src'),
    },
  },
})
