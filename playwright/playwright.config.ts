const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  timeout: 90_000,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8000',
    screenshot: 'on',
    video: 'on',
    trace: 'on',
    channel: 'chrome',  // use existing Chrome — don't install Playwright browsers
  },
});
