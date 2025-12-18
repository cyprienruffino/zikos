import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['static/src/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['static/src/**/*.ts'],
      exclude: ['static/src/**/*.{test,spec}.ts', 'static/**/*.js'],
    },
  },
  resolve: {
    alias: {
      '@': './static/src',
    },
  },
});
