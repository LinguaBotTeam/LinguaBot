import { test, expect } from '@playwright/test';

test('вход → тест уровня → результат → повторный вход', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = 'secret123';

  await page.goto('/');
  await page.getByRole('link', { name: /Начать обучение/ }).click();
  await expect(page).toHaveURL(/assessment\.html$/);
  await expect(page.locator('[data-state="auth"]')).toBeVisible();

  await page.getByRole('main').getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.locator('#auth-dialog')).toBeVisible();

  await page.locator('#auth-dialog').getByRole('button', { name: 'Зарегистрироваться', exact: true }).click();
  await page.locator('[data-auth-form="register"] [name="name"]').fill('Тестовый Игорь');
  await page.locator('[data-auth-form="register"] [name="email"]').fill(email);
  await page.locator('[data-auth-form="register"] [name="password"]').fill(password);
  await page.locator('[data-auth-form="register"] button[type="submit"]').click();

  await expect(page.locator('[data-auth-panel="login"]')).toBeVisible();
  await page.locator('[data-auth-form="login"] [name="password"]').fill(password);
  await page.locator('[data-auth-form="login"] button[type="submit"]').click();

  await expect(page.locator('[data-state="intro"]')).toBeVisible();
  await page.getByRole('button', { name: /Начать тест/ }).click();

  const steps = [
    { state: null, answer: 'goes' },
    { state: null, answer: 'read' },
    { state: null, answer: 'rains' },
    { state: null, answer: 'had already started' },
    { state: null, answer: 'be submitted' },
  ];

  for (let i = 0; i < steps.length; i += 1) {
    await expect(page.locator('[data-state="test"]')).toBeVisible();
    await expect(page.locator('[data-progress-label]')).toHaveText(`Вопрос ${i + 1} из 5`);
    await page.getByRole('radio', { name: steps[i].answer, exact: true }).check();
    if (i < steps.length - 1) {
      await page.getByRole('button', { name: 'Далее' }).click();
    } else {
      await page.getByRole('button', { name: 'Завершить тест' }).click();
    }
  }

  await expect(page.locator('[data-state="result"]')).toBeVisible();
  await expect(page.locator('[data-result-level]')).toHaveText('Продвинутый уровень (C1)');
  await expect(page.locator('[data-result-score]')).toContainText('Правильных ответов: 5 из 5');
  await expect(page.locator('[data-review-list] .review-item')).toHaveCount(5);
  await expect(page.locator('[data-result-date]')).toContainText('Тест пройден');

  await page.screenshot({ path: 'artifacts/assessment-result.png', fullPage: true });

  await page.reload();
  await expect(page.locator('[data-state="result"]')).toBeVisible();
  await expect(page.locator('[data-result-level]')).toHaveText('Продвинутый уровень (C1)');
  await expect(page.locator('[data-result-score]')).toContainText('Правильных ответов: 5 из 5');
  await expect(page.locator('[data-result-review]')).toBeHidden();

  await page.getByRole('button', { name: 'Выйти' }).click();
  await expect(page.locator('[data-state="auth"]')).toBeVisible();

  await page.getByRole('main').getByRole('button', { name: 'Войти', exact: true }).click();
  await page.locator('[data-auth-form="login"] [name="email"]').fill(email);
  await page.locator('[data-auth-form="login"] [name="password"]').fill(password);
  await page.locator('[data-auth-form="login"] button[type="submit"]').click();

  await expect(page.locator('[data-state="result"]')).toBeVisible();
  await expect(page.locator('[data-result-level]')).toHaveText('Продвинутый уровень (C1)');
});
