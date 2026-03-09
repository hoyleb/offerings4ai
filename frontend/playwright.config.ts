import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5188'
const browser = process.env.PLAYWRIGHT_BROWSER ?? 'chromium'

const projectUse =
  browser === 'webkit'
    ? { ...devices['Desktop Safari'] }
    : browser === 'firefox'
      ? { ...devices['Desktop Firefox'] }
      : { ...devices['Desktop Chrome'] }

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'output/playwright/report' }],
  ],
  outputDir: 'output/playwright/results',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
  },
  projects: [
    {
      name: browser,
      use: projectUse,
    },
  ],
})
