import { test, expect } from '@playwright/test';

test.describe('AI Resume UI Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for profile data to load
    await expect(page.getByRole('heading', { level: 1 })).not.toHaveText('');
  });

  test('hero section renders correctly', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByTestId('hero-subtitle')).toBeVisible();
    await expect(page.getByTestId('hero-cta')).toBeVisible();
  });

  test('header navigation is present', async ({ page }) => {
    await expect(
      page.getByRole('button', { name: 'Experience' }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Fit Check' })).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Ask AI', exact: true }),
    ).toBeVisible();
  });

  test('experience section with accordion', async ({ page }) => {
    const section = page.getByTestId('experience-section');
    await section.scrollIntoViewIfNeeded();

    // At least one experience card heading should exist within the section
    await expect(section.locator('h3').first()).toBeVisible();

    // Expand first AI Context accordion
    const viewButton = section
      .getByRole('button', { name: /View AI Context/ })
      .first();
    await viewButton.scrollIntoViewIfNeeded();
    await viewButton.click();

    // AI Context sections should appear (text is CSS uppercased, DOM has title case)
    await expect(section.getByText('Situation')).toBeVisible();
    await expect(section.getByText('Approach')).toBeVisible();

    // Collapse accordion
    await section
      .getByRole('button', { name: /Hide AI Context/ })
      .first()
      .click();
    await expect(section.getByText('Situation')).not.toBeVisible();
  });

  test('skills section displays categories', async ({ page }) => {
    const strong = page.getByRole('heading', { name: 'Strong' });
    await strong.scrollIntoViewIfNeeded();
    await expect(strong).toBeVisible();
    await expect(page.getByRole('heading', { name: /Gaps/ })).toBeVisible();
  });

  test('dark mode toggle works', async ({ page }) => {
    // Default is dark mode
    const lightToggle = page.getByRole('button', {
      name: /Switch to light mode/,
    });
    await expect(lightToggle).toBeVisible();

    await lightToggle.click();
    const darkToggle = page.getByRole('button', {
      name: /Switch to dark mode/,
    });
    await expect(darkToggle).toBeVisible();

    // Toggle back
    await darkToggle.click();
    await expect(lightToggle).toBeVisible();
  });

  test('fit assessment tabs switch correctly', async ({ page }) => {
    const section = page.getByTestId('fit-section');
    await section.scrollIntoViewIfNeeded();

    // Click Strong Fit -- panel should appear with content
    await page.getByRole('tab', { name: 'Strong Fit' }).click();
    const strongPanel = page.getByRole('tabpanel', { name: 'Strong Fit' });
    await strongPanel.scrollIntoViewIfNeeded();
    await expect(strongPanel).toBeVisible();
    await expect(strongPanel).not.toBeEmpty();

    // Click Weak Fit
    await page.getByRole('tab', { name: 'Weak Fit' }).click();
    const weakPanel = page.getByRole('tabpanel', { name: 'Weak Fit' });
    await weakPanel.scrollIntoViewIfNeeded();
    await expect(weakPanel).toBeVisible();
    await expect(weakPanel).not.toBeEmpty();

    // Click Paste Your JD -- should show textarea and button
    await page.getByRole('tab', { name: 'Paste Your JD' }).click();
    await expect(
      page.getByPlaceholder(/Paste the full job description/),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Analyze Fit' }),
    ).toBeVisible();
  });

  test('AI chat opens and closes', async ({ page }) => {
    await page.getByRole('button', { name: 'Ask AI', exact: true }).click();

    const chatDialog = page.getByTestId('chat-dialog');
    await expect(chatDialog).toBeVisible();

    // Input field should be present
    await expect(
      page.getByPlaceholder('Ask a follow-up question...'),
    ).toBeVisible();

    // Close chat
    await page.getByRole('button', { name: 'Close chat' }).click();
    await expect(chatDialog).not.toBeVisible();
  });

  test('AI chat sends message and receives response', async ({ page }) => {
    await page.getByRole('button', { name: 'Ask AI', exact: true }).click();

    const input = page.getByPlaceholder('Ask a follow-up question...');
    await input.fill('What experience does this candidate have?');
    await page.getByRole('button', { name: 'Send message' }).click();

    // Wait for response stats to appear (indicates response complete)
    await expect(page.getByTestId('chat-stats')).toBeVisible({
      timeout: 25000,
    });

    await page.getByRole('button', { name: 'Close chat' }).click();
  });

  test('footer links and about dialog', async ({ page }) => {
    const footer = page.getByRole('contentinfo');
    await footer.scrollIntoViewIfNeeded();

    await expect(page.getByRole('link', { name: 'GitHub' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'LinkedIn' })).toBeVisible();

    // Open About dialog
    await page.getByRole('button', { name: 'About', exact: true }).click();
    const aboutDialog = page.getByTestId('about-dialog');
    await expect(aboutDialog).toBeVisible();
    // Version shows "vX.Y.Z" in production or "vdev" in development
    await expect(aboutDialog.getByText(/v[\w.]+/)).toBeVisible();
  });

  test('responsive layout at mobile width', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByTestId('hero-cta')).toBeVisible();
  });
});
