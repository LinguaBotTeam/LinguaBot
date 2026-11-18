(function () {
  const api = window.LinguaBotAPI;
  const root = document.querySelector('[data-exercise]');
  if (!api || !root) {
    return;
  }

  const states = {};
  root.querySelectorAll('[data-state]').forEach(function (node) {
    states[node.dataset.state] = node;
  });

  const form = root.querySelector('[data-exercise-form]');
  const optionsBox = root.querySelector('[data-exercise-options]');
  const prompt = root.querySelector('[data-exercise-prompt]');
  const topic = root.querySelector('[data-exercise-topic]');
  const difficulty = root.querySelector('[data-exercise-difficulty]');
  const source = root.querySelector('[data-exercise-source]');
  const exerciseError = root.querySelector('[data-exercise-error]');
  const feedback = root.querySelector('[data-exercise-feedback]');
  const verdict = root.querySelector('[data-exercise-verdict]');
  const answerLine = root.querySelector('[data-exercise-answer]');
  const explanation = root.querySelector('[data-exercise-explanation]');
  const checkButton = root.querySelector('[data-exercise-check]');
  const nextButton = root.querySelector('[data-exercise-next]');
  const errorMessage = root.querySelector('[data-error-message]');

  const DIFFICULTY_LABELS = {
    beginner: 'Начальный уровень',
    intermediate: 'Средний уровень',
    advanced: 'Продвинутый уровень',
  };

  let current = null;
  let seen = [];
  let answered = false;
  let checking = false;

  function showState(name) {
    Object.keys(states).forEach(function (key) {
      states[key].hidden = key !== name;
    });
  }

  function openAuth(mode) {
    if (window.LinguaBotAuth) {
      window.LinguaBotAuth.open(mode);
    }
  }

  function showErrorState(message) {
    errorMessage.textContent =
      message || 'Произошла ошибка. Попробуйте ещё раз.';
    showState('error');
  }

  function showFormError(message) {
    exerciseError.textContent = message;
    exerciseError.hidden = false;
  }

  function clearFormError() {
    exerciseError.textContent = '';
    exerciseError.hidden = true;
  }

  function setOptionsDisabled(disabled) {
    optionsBox.setAttribute('aria-disabled', String(disabled));
    optionsBox.querySelectorAll('input').forEach(function (input) {
      input.disabled = disabled;
    });
  }

  function renderExercise(exercise) {
    if (seen.indexOf(exercise.id) !== -1) {
      seen = [];
    }
    current = exercise;
    answered = false;
    checking = false;

    difficulty.textContent =
      DIFFICULTY_LABELS[exercise.difficulty] || exercise.difficulty;
    topic.textContent = exercise.topic || '';
    source.textContent =
      exercise.level_source === 'test'
        ? 'Сложность подобрана по результату теста уровня.'
        : 'Тест ещё не пройден — показываем начальный уровень. Пройдите тест, чтобы подобрать сложность.';
    prompt.textContent = exercise.prompt;
    clearFormError();

    optionsBox.replaceChildren();
    (exercise.options || []).forEach(function (option) {
      const label = document.createElement('label');
      label.className = 'option';

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'exercise-answer';
      input.value = String(option.id);
      input.addEventListener('change', clearFormError);

      const text = document.createElement('span');
      text.textContent = option.text;

      label.append(input, text);
      optionsBox.append(label);
    });
    setOptionsDisabled(false);

    feedback.hidden = true;
    verdict.className = 'exercise-verdict';
    verdict.textContent = '';
    answerLine.textContent = '';
    explanation.textContent = '';
    checkButton.hidden = false;
    checkButton.disabled = false;
    checkButton.textContent = 'Проверить';

    showState('exercise');
  }

  function renderFeedback(result) {
    answered = true;
    checking = false;
    if (seen.indexOf(current.id) === -1) {
      seen.push(current.id);
    }
    setOptionsDisabled(true);

    verdict.className =
      'exercise-verdict ' + (result.correct ? 'is-correct' : 'is-wrong');
    verdict.textContent = result.correct ? 'Верно!' : 'Неверно';
    answerLine.textContent = result.correct
      ? 'Вы выбрали: ' + result.correct_text
      : 'Правильный ответ: ' + result.correct_text;
    explanation.textContent = result.explanation || '';
    feedback.hidden = false;
    checkButton.hidden = true;
  }

  async function load() {
    if (!api.getToken()) {
      showState('auth');
      return;
    }

    showState('loading');
    try {
      const exercise = await api.getNextExercise(seen);
      if (!exercise || !exercise.id) {
        throw new Error('Сервер не вернул упражнение.');
      }
      renderExercise(exercise);
    } catch (error) {
      if (error && error.code === 'unauthorized') {
        api.clearSession();
        showState('auth');
      } else {
        showErrorState(error.message);
      }
    }
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (answered || checking || !current) {
      return;
    }

    const selected = optionsBox.querySelector(
      'input[name="exercise-answer"]:checked',
    );
    if (!selected) {
      showFormError('Выберите вариант ответа.');
      return;
    }

    clearFormError();
    checking = true;
    checkButton.disabled = true;
    checkButton.textContent = 'Проверяем…';

    try {
      const result = await api.submitExerciseAnswer(
        current.id,
        Number(selected.value),
      );
      renderFeedback(result);
    } catch (error) {
      checking = false;
      if (error && error.code === 'unauthorized') {
        api.clearSession();
        showState('auth');
      } else {
        checkButton.disabled = false;
        checkButton.textContent = 'Проверить';
        showFormError(error.message || 'Не удалось проверить ответ.');
      }
    }
  });

  nextButton.addEventListener('click', function () {
    load();
  });

  root.querySelectorAll('[data-open-login]').forEach(function (button) {
    button.addEventListener('click', function () {
      openAuth('login');
    });
  });

  root.querySelectorAll('[data-open-register]').forEach(function (button) {
    button.addEventListener('click', function () {
      openAuth('register');
    });
  });

  root.querySelectorAll('[data-exercise-retry]').forEach(function (button) {
    button.addEventListener('click', load);
  });

  document.addEventListener('linguabot:auth-changed', load);

  load();
})();
