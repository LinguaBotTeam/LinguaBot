import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 390, height: 844 } });

test('мобильный экран теста без горизонтальной прокрутки', async ({ page }) => {
  await page.goto('/assessment.html');
  await expect(page.locator('[data-state="auth"]')).toBeVisible();
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(1);
});
