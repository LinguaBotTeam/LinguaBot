import { test, expect } from '@playwright/test';

test('результат теста → чат «В кафе» → исправление → сохранённая переписка', async ({ page }) => {
  const email = `chat-e2e-${Date.now()}@example.com`;
  const password = 'secret123';

  await page.goto('/assessment.html');
  await expect(page.locator('[data-state="auth"]')).toBeVisible();
  await page.getByRole('main').getByRole('button', { name: 'Войти', exact: true }).click();
  await page.locator('#auth-dialog').getByRole('button', { name: 'Зарегистрироваться', exact: true }).click();
  await page.locator('[data-auth-form="register"] [name="name"]').fill('Тест Чата');
  await page.locator('[data-auth-form="register"] [name="email"]').fill(email);
  await page.locator('[data-auth-form="register"] [name="password"]').fill(password);
  await page.locator('[data-auth-form="register"] button[type="submit"]').click();
  await page.locator('[data-auth-form="login"] [name="password"]').fill(password);
  await page.locator('[data-auth-form="login"] button[type="submit"]').click();

  await expect(page.locator('[data-state="intro"]')).toBeVisible();
  await page.getByRole('button', { name: /Начать тест/ }).click();

  const answers = ['goes', 'read', 'rains', 'had already started', 'be submitted'];
  for (let i = 0; i < answers.length; i += 1) {
    await page.getByRole('radio', { name: answers[i], exact: true }).check();
    await page.getByRole('button', {
      name: i === answers.length - 1 ? 'Завершить тест' : 'Далее',
    }).click();
  }

  await expect(page.locator('[data-state="result"]')).toBeVisible();
  await page.getByRole('link', { name: /Перейти к чату/ }).click();
  await expect(page).toHaveURL(/chat\.html$/);
  await expect(page.locator('[data-chat-workspace]')).toBeVisible();
  await expect(page.locator('[data-chat-list-empty]')).toBeVisible();

  await page.getByRole('button', { name: /Новый диалог/ }).click();
  await expect(page.locator('[data-chat-name]')).toHaveText('В кафе');
  await expect(page.locator('[data-chat-form]')).toBeVisible();
  await expect(page.locator('[data-chat-example]')).toBeVisible();

  await page.locator('[data-chat-form] textarea').fill('I would likes a tea.');
  await page.getByRole('button', { name: /Отправить/ }).click();

  await expect(page.locator('[data-chat-messages] li')).toHaveCount(2);
  await expect(page.locator('[data-chat-messages] li').first()).toContainText('I would likes a tea.');
  await expect(page.locator('[data-chat-messages] li').first()).toContainText('Предлагаемое исправление');
  await expect(page.locator('[data-chat-messages] li').first()).toContainText('like');
  await expect(page.locator('[data-chat-messages] li').nth(1)).toContainText('Of course. Would you like milk with that?');

  await page.reload();
  await expect(page.locator('[data-chat-messages] li')).toHaveCount(2);
  await expect(page.locator('[data-chat-messages] li').first()).toContainText('I would likes a tea.');
  await expect(page.locator('[data-chat-messages] li').first()).toContainText('Предлагаемое исправление');
  await expect(page.locator('[data-chat-name]')).toHaveText('В кафе');

  await page.screenshot({ path: 'artifacts/chat-saved.png', fullPage: true });
});
