(function () {
  const api = window.LinguaBotAPI;
  const root = document.querySelector('[data-assessment]');
  if (!api || !root) {
    return;
  }

  const states = {};
  root.querySelectorAll('[data-state]').forEach(function (node) {
    states[node.dataset.state] = node;
  });

  const testForm = root.querySelector('[data-test-form]');
  const questionText = root.querySelector('[data-question-text]');
  const optionsBox = root.querySelector('[data-options]');
  const progressLabel = root.querySelector('[data-progress-label]');
  const progressBar = root.querySelector('[data-progress-bar]');
  const backButton = root.querySelector('[data-back]');
  const nextButton = root.querySelector('[data-next]');
  const testError = root.querySelector('[data-test-error]');
  const resultLevel = root.querySelector('[data-result-level]');
  const resultScore = root.querySelector('[data-result-score]');
  const resultDate = root.querySelector('[data-result-date]');
  const resultReview = root.querySelector('[data-result-review]');
  const reviewList = root.querySelector('[data-review-list]');
  const errorMessage = root.querySelector('[data-error-message]');

  const LEVEL_LABELS = {
    beginner: 'Начальный уровень',
    intermediate: 'Средний уровень',
    advanced: 'Продвинутый уровень',
  };

  let questions = [];
  let answers = {};
  let currentIndex = 0;

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

  function showTestError(message) {
    testError.textContent = message;
    testError.hidden = false;
  }

  function clearTestError() {
    testError.textContent = '';
    testError.hidden = true;
  }

  function formatDate(value) {
    if (!value) {
      return '';
    }
    const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(value);
    const date = new Date(hasZone ? value : value + 'Z');
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  function levelTitle(level, cefr) {
    const label = LEVEL_LABELS[level] || level || 'Уровень';
    return cefr ? label + ' (' + cefr + ')' : label;
  }

  function renderResult(result, askedQuestions) {
    resultLevel.textContent = levelTitle(result.level, result.cefr);

    const items = Array.isArray(result.questions) ? result.questions : [];
    const correctCount = items.filter(function (item) {
      return item.correct;
    }).length;
    resultScore.textContent =
      'Правильных ответов: ' +
      correctCount +
      ' из ' +
      items.length +
      ' · ' +
      result.score +
      '%';

    const dateText = formatDate(result.taken_at);
    resultDate.textContent = dateText ? 'Тест пройден: ' + dateText : '';

    reviewList.replaceChildren();
    const canReview = items.length > 0 && Array.isArray(askedQuestions);
    resultReview.hidden = !canReview;
    if (!canReview) {
      return;
    }

    const questionsById = {};
    askedQuestions.forEach(function (question) {
      questionsById[question.id] = question;
    });

    items.forEach(function (item) {
      const question = questionsById[item.question_id];
      if (!question) {
        return;
      }

      const listItem = document.createElement('li');
      listItem.className = 'review-item';

      const verdict = document.createElement('span');
      verdict.className =
        'review-verdict ' + (item.correct ? 'is-correct' : 'is-wrong');
      verdict.textContent = item.correct ? 'Верно' : 'Есть ошибка';

      const questionLine = document.createElement('p');
      questionLine.className = 'review-question';
      questionLine.textContent = question.text;

      listItem.append(verdict, questionLine);

      if (!item.correct) {
        const correctOption = (question.options || []).find(function (option) {
          return option.id === item.correct_option_id;
        });
        if (correctOption) {
          const answerLine = document.createElement('p');
          answerLine.className = 'review-answer';
          answerLine.textContent = 'Правильный ответ: ' + correctOption.text;
          listItem.append(answerLine);
        }
      }

      reviewList.append(listItem);
    });
  }

  function updateNextLabel() {
    nextButton.textContent =
      currentIndex === questions.length - 1 ? 'Завершить тест' : 'Далее';
  }

  function renderQuestion() {
    const question = questions[currentIndex];
    if (!question) {
      return;
    }

    progressLabel.textContent =
      'Вопрос ' + (currentIndex + 1) + ' из ' + questions.length;
    progressBar.style.width =
      ((currentIndex + 1) / questions.length) * 100 + '%';
    questionText.textContent = question.text;
    clearTestError();

    optionsBox.replaceChildren();
    (question.options || []).forEach(function (option) {
      const label = document.createElement('label');
      label.className = 'option';

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'assessment-answer';
      input.value = String(option.id);
      input.checked = answers[question.id] === option.id;
      input.addEventListener('change', function () {
        answers[question.id] = option.id;
        clearTestError();
      });

      const text = document.createElement('span');
      text.textContent = option.text;

      label.append(input, text);
      optionsBox.append(label);
    });

    backButton.disabled = currentIndex === 0;
    nextButton.disabled = false;
    updateNextLabel();
  }

  function saveAnswer() {
    const question = questions[currentIndex];
    const selected = optionsBox.querySelector('input[name="assessment-answer"]:checked');
    if (selected) {
      answers[question.id] = Number(selected.value);
    }
    return Boolean(answers[question.id]);
  }

  async function submitAnswers() {
    const missing = questions.some(function (question) {
      return !answers[question.id];
    });
    if (missing) {
      showTestError('Ответьте на все вопросы теста.');
      return;
    }

    nextButton.disabled = true;
    nextButton.textContent = 'Отправляем…';

    try {
      const payload = questions.map(function (question) {
        return {
          question_id: question.id,
          option_id: answers[question.id],
        };
      });
      const result = await api.submitTest(payload);
      renderResult(result, questions);
      showState('result');
    } catch (error) {
      if (error && error.code === 'unauthorized') {
        api.clearSession();
        showState('auth');
      } else {
        showTestError(error.message || 'Не удалось отправить ответы.');
        nextButton.disabled = false;
        updateNextLabel();
      }
    }
  }

  async function startTest() {
    showState('loading');
    try {
      const payload = await api.getQuestions();
      questions = Array.isArray(payload.questions) ? payload.questions : [];
      if (questions.length === 0) {
        throw new Error('Сервер не вернул вопросы теста.');
      }
      answers = {};
      currentIndex = 0;
      renderQuestion();
      showState('test');
    } catch (error) {
      if (error && error.code === 'unauthorized') {
        api.clearSession();
        showState('auth');
      } else {
        showErrorState(error.message);
      }
    }
  }

  async function load() {
    if (!api.getToken()) {
      showState('auth');
      return;
    }

    showState('loading');
    try {
      const result = await api.getResult();
      renderResult(result, null);
      showState('result');
    } catch (error) {
      if (error && error.code === 'result_not_found') {
        showState('intro');
      } else if (error && error.code === 'unauthorized') {
        api.clearSession();
        showState('auth');
      } else {
        showErrorState(error.message);
      }
    }
  }

  testForm.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!saveAnswer()) {
      showTestError('Выберите вариант ответа.');
      return;
    }
    clearTestError();

    if (currentIndex < questions.length - 1) {
      currentIndex += 1;
      renderQuestion();
      return;
    }

    submitAnswers();
  });

  backButton.addEventListener('click', function () {
    if (currentIndex > 0) {
      currentIndex -= 1;
      renderQuestion();
    }
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

  root.querySelectorAll('[data-start-test]').forEach(function (button) {
    button.addEventListener('click', startTest);
  });

  root.querySelectorAll('[data-retry]').forEach(function (button) {
    button.addEventListener('click', startTest);
  });

  root.querySelectorAll('[data-retry-load]').forEach(function (button) {
    button.addEventListener('click', load);
  });

  document.addEventListener('linguabot:auth-changed', load);

  load();
})();
