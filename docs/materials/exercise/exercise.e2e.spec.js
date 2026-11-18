import { test, expect } from '@playwright/test';

const CORRECT = [
  { question_id: 1, option_id: 2 },
  { question_id: 2, option_id: 1 },
  { question_id: 3, option_id: 1 },
  { question_id: 4, option_id: 3 },
  { question_id: 5, option_id: 1 },
];

const WRONG = [
  { question_id: 1, option_id: 1 },
  { question_id: 2, option_id: 2 },
  { question_id: 3, option_id: 2 },
  { question_id: 4, option_id: 1 },
  { question_id: 5, option_id: 2 },
];

const scenarios = [
  {
    difficulty: 'beginner',
    label: 'Начальный уровень',
    assessment: WRONG,
    correct: 'goes',
    wrong: 'go',
  },
  {
    difficulty: 'intermediate',
    label: 'Средний уровень',
    assessment: CORRECT.slice(0, 3).concat(WRONG.slice(3)),
    correct: 'have lived',
    wrong: 'live',
  },
  {
    difficulty: 'advanced',
    label: 'Продвинутый уровень',
    assessment: CORRECT,
    correct: 'had already started',
    wrong: 'already started',
  },
];

test('обратная связь на верный и неверный ответ по трём уровням', async ({
  page,
  request,
}) => {
  for (const scenario of scenarios) {
    const email = `ex-${scenario.difficulty}-${Date.now()}@example.com`;
    const register = await request.post('/api/v1/auth/register', {
      data: { name: 'Демо', email, password: 'secret123' },
    });
    expect(register.status()).toBe(201);

    const login = await request.post('/api/v1/auth/login', {
      data: { email, password: 'secret123' },
    });
    const session = await login.json();

    const submitted = await request.post('/api/v1/assessment/submit', {
      headers: { Authorization: `Bearer ${session.access_token}` },
      data: { answers: scenario.assessment },
    });
    expect(submitted.status()).toBe(201);

    await page.goto('/exercise.html');
    await page.evaluate(
      ([token, user]) => {
        localStorage.setItem('linguabot-token', token);
        localStorage.setItem('linguabot-user', JSON.stringify(user));
      },
      [session.access_token, session.user],
    );
    await page.reload();

    await expect(page.locator('[data-state="exercise"]')).toBeVisible();
    await expect(page.locator('[data-exercise-difficulty]')).toHaveText(
      scenario.label,
    );
    await expect(page.locator('[data-exercise-source]')).toContainText(
      'по результату теста',
    );

    await page
      .getByRole('radio', { name: scenario.correct, exact: true })
      .check();
    await page.getByRole('button', { name: 'Проверить' }).click();
    await expect(page.locator('[data-exercise-verdict]')).toHaveText('Верно!');
    await expect(page.locator('[data-exercise-answer]')).toContainText(
      scenario.correct,
    );
    await expect(page.locator('[data-exercise-explanation]')).not.toBeEmpty();
    await page.screenshot({
      path: `artifacts/exercise-${scenario.difficulty}-correct.png`,
      fullPage: true,
    });

    await page.reload();
    await expect(page.locator('[data-state="exercise"]')).toBeVisible();
    await expect(page.locator('[data-exercise-difficulty]')).toHaveText(
      scenario.label,
    );

    await page
      .getByRole('radio', { name: scenario.wrong, exact: true })
      .check();
    await page.getByRole('button', { name: 'Проверить' }).click();
    await expect(page.locator('[data-exercise-verdict]')).toHaveText('Неверно');
    await expect(page.locator('[data-exercise-answer]')).toContainText(
      'Правильный ответ: ' + scenario.correct,
    );
    await expect(page.locator('[data-exercise-explanation]')).not.toBeEmpty();
    await page.screenshot({
      path: `artifacts/exercise-${scenario.difficulty}-wrong.png`,
      fullPage: true,
    });
  }
});
