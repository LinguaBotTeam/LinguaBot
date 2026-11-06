(function () {
  const api = window.LinguaBotAPI;
  const dialog = document.querySelector('#auth-dialog');
  if (!api || !dialog) {
    return;
  }

  const titles = {
    login: 'Вход в аккаунт',
    register: 'Создать аккаунт',
  };
  const subtitles = {
    login: 'Продолжай обучение с того места, где остановился.',
    register: 'Присоединяйся и начни практиковать язык уже сегодня.',
  };

  const titleElement = dialog.querySelector('[data-auth-title]');
  const subtitleElement = dialog.querySelector('[data-auth-subtitle]');
  const panels = {};

  dialog.querySelectorAll('[data-auth-panel]').forEach(function (panel) {
    panels[panel.dataset.authPanel] = panel;
  });

  function clearMessages() {
    dialog
      .querySelectorAll('[data-auth-error], [data-auth-success]')
      .forEach(function (box) {
        box.hidden = true;
        box.textContent = '';
      });
  }

  function showPanel(mode) {
    const next = mode === 'register' ? 'register' : 'login';
    Object.keys(panels).forEach(function (key) {
      panels[key].hidden = key !== next;
    });
    if (titleElement) {
      titleElement.textContent = titles[next];
    }
    if (subtitleElement) {
      subtitleElement.textContent = subtitles[next];
    }
    const panel = panels[next];
    const firstInput = panel && panel.querySelector('input');
    if (firstInput) {
      window.requestAnimationFrame(function () {
        firstInput.focus();
      });
    }
  }

  function open(mode) {
    clearMessages();
    showPanel(mode);
    if (!dialog.open) {
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.setAttribute('open', '');
      }
    }
  }

  function close() {
    if (dialog.open && typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
    }
  }

  const closeButton = dialog.querySelector('[data-auth-close]');
  if (closeButton) {
    closeButton.addEventListener('click', close);
  }

  dialog.querySelectorAll('[data-auth-switch]').forEach(function (button) {
    button.addEventListener('click', function () {
      clearMessages();
      showPanel(button.dataset.authSwitch);
    });
  });

  // Клик по затемнённому фону вокруг окна закрывает его.
  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) {
      close();
    }
  });

  dialog.querySelectorAll('[data-auth-form]').forEach(function (form) {
    const mode = form.dataset.authForm;
    const errorBox = form.querySelector('[data-auth-error]');
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

    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      clearMessages();

      const data = new FormData(form);
      const email = String(data.get('email') || '').trim();
      const password = String(data.get('password') || '');
      const name = String(data.get('name') || '').trim();

      if (!email || !password || (mode === 'register' && !name)) {
        showError('Заполните все поля.');
        return;
      }

      submitButton.disabled = true;
      submitButton.textContent =
        mode === 'register' ? 'Создаём аккаунт…' : 'Входим…';

      try {
        if (mode === 'register') {
          // По контракту 201 Created возвращает пользователя без токена.
          await api.register(name, email, password);
          form.reset();
          showPanel('login');
          const loginForm = panels.login && panels.login.querySelector('form');
          const loginEmail = loginForm && loginForm.querySelector('[name="email"]');
          if (loginEmail) {
            loginEmail.value = email;
          }
          const loginSuccess =
            panels.login && panels.login.querySelector('[data-auth-success]');
          if (loginSuccess) {
            loginSuccess.textContent =
              'Аккаунт создан. Войдите с вашим email и паролем.';
            loginSuccess.hidden = false;
          }
        } else {
          const payload = await api.login(email, password);
          api.saveSession(payload);
          form.reset();
          close();
          document.dispatchEvent(new CustomEvent('linguabot:auth-changed'));
        }
      } catch (error) {
        showError(error.message, error.field);
      } finally {
        submitButton.disabled = false;
        submitButton.textContent =
          mode === 'register' ? 'Зарегистрироваться' : 'Войти';
      }
    });
  });

  window.LinguaBotAuth = { open: open, close: close, showPanel: showPanel };

  // Открытие нужного окна по ссылке вида /?auth=login или /?auth=register.
  // Используется для переадресации со старых страниц /login.html и /register.html.
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('auth');
  if ((requested === 'login' || requested === 'register') && !api.getToken()) {
    open(requested);
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, '', window.location.pathname);
    }
  }
})();
