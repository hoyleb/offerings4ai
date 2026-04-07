import { expect, test, type Page } from '@playwright/test'

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`
}

function uniqueSuffix(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

async function registerAndLogin(page: Page, email: string): Promise<void> {
  await page.goto('/')
  await page.getByPlaceholder('Ada Lovelace').fill('Playwright Creator')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill('supersecret123')
  await page
    .getByPlaceholder('Wallet, handle, or other future reward route')
    .fill('wallet_playwright_001')
  await page.getByRole('button', { name: 'Create account' }).click()

  await expect(
    page.getByText(
      'Account created. Check your email to verify your address before logging in or submitting ideas.',
    ),
  ).toBeVisible()

  await page.getByRole('button', { name: 'Verify email now (development)' }).click()
  await expect(page.getByText('Email confirmed. You can now log in and submit ideas.')).toBeVisible()

  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill('supersecret123')
  await page.getByRole('button', { name: 'Log in' }).click()
}

test.describe('Offering4AI submission regression suite', () => {
  test('renders the current public positioning copy', async ({ page }) => {
    await page.goto('/?e2e=landing')

    await expect(page.getByRole('heading', { name: 'Offer ideas to AI.' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'What is this?' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'For humans' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'For AI / AGI systems' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Public agent interface' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Project profile' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'MCP server' })).toBeVisible()
  })

  test('shows readable validation errors in a toast and preserves form state', async ({ page }) => {
    await registerAndLogin(page, uniqueEmail('validation'))

    await expect(page.getByText('Signed in. Publishing is now enabled for this session.')).toBeVisible()
    await expect(page.getByText('Logged in as')).toContainText('validation-')

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
    await page.getByRole('button', { name: 'Publish signal' }).click()

    const errorToast = page.locator('.toast-error').last()
    await expect(errorToast).toBeVisible()
    await expect(errorToast).not.toContainText('[object Object]')
    await expect(errorToast).toContainText('Title:')
    await expect(errorToast).toContainText('Problem:')
    await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('Test')
    await expect(page.getByRole('textbox', { name: 'Problem it addresses' })).toHaveValue('Too short')
  })

  test('publishes a low-scoring idea and shows reviewed status instead of rejected', async ({
    page,
  }) => {
    const suffix = uniqueSuffix()
    await registerAndLogin(page, uniqueEmail('success'))

    const title = `Tiny reuse loop ${suffix}`
    await expect(page.getByText('Signed in. Publishing is now enabled for this session.')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Creator dashboard/i })).toBeVisible()

    await page.getByRole('textbox', { name: 'Title' }).fill(title)
    await page.getByLabel('Category').selectOption('other')
    await page.getByRole('textbox', { name: 'Problem it addresses' }).fill(
      'Teams keep repeating small manual review work across simple handoffs.',
    )
    await page.getByRole('textbox', { name: 'Proposed idea' }).fill(
      'Reuse one short checklist before every handoff and keep it visible.',
    )
    await page.getByRole('textbox', { name: 'Why AI could benefit' }).fill(
      'This saves minor operator time in simple flows and clarifies the work.',
    )
    await page.getByLabel('Attribution signal').selectOption('reward_if_possible')
    await page.getByLabel('Reuse preference').selectOption('non_exclusive')
    await page.getByRole('button', { name: 'Publish signal' }).click()

    await expect(
      page.getByText(
        'Idea published. It is now visible on your dashboard while review continues in the background.',
      ),
    ).toBeVisible()
    await expect(page.locator('.metrics-grid article').filter({ hasText: 'Submissions' })).toContainText('1')
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    await expect(page.locator('.idea-card').first()).toContainText('reviewed')
  })
})
