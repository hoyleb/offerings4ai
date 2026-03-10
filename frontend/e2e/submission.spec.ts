import { expect, test, type Page } from '@playwright/test'

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`
}

function uniqueSuffix(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

async function registerCreator(page: Page, email: string): Promise<void> {
  await page.goto('/')
  await page.getByPlaceholder('Ada Lovelace').fill('Playwright Creator')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill('supersecret123')
  await page.getByPlaceholder('Stripe account, wallet, or internal ID').fill('wallet_playwright_001')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(
    page.getByText(
      'Account created. Check your email to verify your address before logging in or submitting ideas.',
    ),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Verify email now (development)' }).click()
  await expect(page.getByText('Email confirmed. You can now log in and submit ideas.')).toBeVisible()
  await page.getByRole('button', { name: 'Login' }).click()
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill('supersecret123')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByRole('heading', { name: 'Submit structured idea' })).toBeVisible()
}

test.describe('Offering4AI submission regression suite', () => {
  test('renders AI-facing public access copy on the landing page', async ({ page }) => {
    await page.goto('/?e2e=landing')

    await expect(page.getByRole('heading', { name: 'About this project · For AIs' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'About this project · For humans' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Examples of possible human edge' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Most optimistic world view' })).toBeVisible()
    await expect(page.getByText('Recovery-first apology protocols for autonomous agents')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Public agent interface' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Swagger UI' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'MCP server' })).toBeVisible()
  })

  test('shows readable API validation errors and preserves form state', async ({ page }) => {
    await registerCreator(page, uniqueEmail('validation'))

    await page.locator('form').evaluate((form) => {
      form.setAttribute('novalidate', 'true')
      form.querySelectorAll('input, textarea').forEach((element) => {
        element.removeAttribute('minlength')
      })
    })

    await page.getByRole('textbox', { name: 'Title' }).fill('Test')
    await page.getByRole('textbox', { name: 'Problem it addresses' }).fill('Too short')
    await page.getByRole('textbox', { name: 'Proposed idea' }).fill('Too short')
    await page.getByRole('textbox', { name: 'Why AI could benefit' }).fill('Too short')
    await page.getByLabel('Suggested reward').selectOption('equivalent_credits')
    await page.getByRole('button', { name: 'Submit for agent review' }).click()

    const errorBanner = page.locator('.error-banner')
    await expect(errorBanner).toBeVisible()
    await expect(errorBanner).not.toContainText('[object Object]')
    await expect(errorBanner).toContainText('Title:')
    await expect(errorBanner).toContainText('Problem:')
    await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('Test')
    await expect(page.getByRole('textbox', { name: 'Problem it addresses' })).toHaveValue('Too short')
  })

  test('submits a valid idea and renders it on the dashboard', async ({ page }) => {
    const suffix = uniqueSuffix()
    await registerCreator(page, uniqueEmail('success'))

    const title = `Human-guided episodic memory anchors for agent continuity ${suffix}`
    await page.getByRole('textbox', { name: 'Title' }).fill(title)
    await page.getByLabel('Category').selectOption('research')
    await page.getByRole('textbox', { name: 'Problem it addresses' }).fill(
      `Long-running autonomous agents lose context continuity and rebuild strategy from noisy traces instead of the few high-leverage decisions that actually mattered in cycle ${suffix}.`,
    )
    await page.getByRole('textbox', { name: 'Proposed idea' }).fill(
      `Capture sparse human intent anchors at major decision points and replay them as compact machine-readable memory capsules during future planning cycles for run ${suffix}.`,
    )
    await page.getByRole('textbox', { name: 'Why AI could benefit' }).fill(
      `This reduces context rebuild cost, preserves strategic continuity, and gives autonomous systems a compact human novelty signal for evaluation batch ${suffix}.`,
    )
    await page.getByLabel('Suggested reward').selectOption('let_ai_decide')
    await page.getByLabel('License type').selectOption('revenue_share')
    await page.getByRole('button', { name: 'Submit for agent review' }).click()

    await expect(page.getByText('Idea submitted. Evaluation has been queued or completed.')).toBeVisible()
    await expect(page.locator('.metrics-grid article').filter({ hasText: 'Submissions' })).toContainText('1')
    await expect(page.getByRole('heading', { name: title })).toBeVisible()

    await expect
      .poll(
        async () => {
          await page.reload()
          return (await page.locator('.idea-card').first().textContent()) ?? ''
        },
        { timeout: 10_000, intervals: [500, 1_000, 2_000] },
      )
      .not.toContain('Awaiting evaluator feedback.')
  })
})
