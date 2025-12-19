import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['frontend/src/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['frontend/src/**/*.ts'],
      exclude: ['frontend/src/**/*.{test,spec}.ts', 'frontend/dist/**/*.js'],
    },
  },
  resolve: {
    alias: {
      '@': './frontend/src',
    },
  },
});
