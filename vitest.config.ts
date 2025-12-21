import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./frontend/tests/setup.ts'],
    include: ['tests/frontend/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['frontend/src/**/*.ts'],
      exclude: ['tests/**/*', 'frontend/dist/**/*.js'],
    },
  },
  resolve: {
    alias: {
      '@': './frontend/src',
    },
  },
});
