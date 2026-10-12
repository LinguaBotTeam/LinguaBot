(function () {
  const api = window.LinguaBotAPI;
  const form = document.querySelector('[data-auth-form]');
  if (!api || !form) {
    return;
  }

  if (api.getToken()) {
    window.location.replace('./index.html');
    return;
  }

  const mode = form.dataset.authForm;
  const errorBox = form.querySelector('[data-auth-error]');
  const successBox = document.querySelector('[data-auth-success]');
  const submitButton = form.querySelector('button[type="submit"]');

  function showError(message, field) {
    if (errorBox) {
      errorBox.textContent = message;
      errorBox.hidden = false;
    }
    if (field) {
      const input = form.querySelector('[name="' + field + '"]');
      if (input) {
        input.focus();
      }
    }
  }

  function clearError() {
    if (!errorBox) {
      return;
    }
    errorBox.hidden = true;
    errorBox.textContent = '';
  }

  if (mode === 'login') {
    const params = new URLSearchParams(window.location.search);
    if (params.get('registered') === '1') {
      if (successBox) {
        successBox.textContent =
          'Аккаунт создан. Войдите с вашим email и паролем.';
        successBox.hidden = false;
      }
      const emailField = form.querySelector('[name="email"]');
      const prefill = params.get('email');
      if (emailField && prefill) {
        emailField.value = prefill;
      }
    }
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    clearError();

    const data = new FormData(form);
    const email = String(data.get('email') || '').trim();
    const password = String(data.get('password') || '');
    const name = String(data.get('name') || '').trim();

    if (!email || !password || (mode === 'register' && !name)) {
      showError('Заполните все поля.');
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = mode === 'register' ? 'Создаём аккаунт…' : 'Входим…';

    try {
      if (mode === 'register') {
        // По контракту 201 Created возвращает пользователя без токена.
        await api.register(name, email, password);
        window.location.replace(
          './login.html?registered=1&email=' + encodeURIComponent(email)
        );
      } else {
        const payload = await api.login(email, password);
        api.saveSession(payload);
        window.location.replace('./index.html');
      }
    } catch (error) {
      showError(error.message, error.field);
      submitButton.disabled = false;
      submitButton.textContent = mode === 'register' ? 'Зарегистрироваться' : 'Войти';
    }
  });
})();
