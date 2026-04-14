import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 90_000,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:8000',
    headless: false,
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'on',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: false,
        launchOptions: {
          executablePath: '/usr/bin/google-chrome',
          args: ['--start-maximized'],
        },
      },
    },
  ],
});
