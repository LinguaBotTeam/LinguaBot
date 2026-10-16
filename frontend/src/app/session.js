(function () {
  const api = window.LinguaBotAPI;
  const container = document.querySelector('[data-auth-actions]');
  if (!api || !container) {
    return;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[char];
    });
  }

  function renderGuest() {
    container.innerHTML =
      '<button class="link-button" type="button" data-auth-open="login">Войти</button>' +
      '<button class="button button-sm" type="button" data-auth-open="register">Регистрация</button>';

    container.querySelectorAll('[data-auth-open]').forEach(function (button) {
      button.addEventListener('click', function () {
        if (window.LinguaBotAuth) {
          window.LinguaBotAuth.open(button.dataset.authOpen);
        }
      });
    });
  }

  function renderUser(user) {
    const name = user && user.name ? user.name : 'Профиль';
    const initial = name.charAt(0).toUpperCase();
    container.innerHTML =
      '<span class="user-chip">' +
        '<span class="user-avatar" aria-hidden="true">' + escapeHtml(initial) + '</span>' +
        escapeHtml(name) +
      '</span>' +
      '<button class="nav-link logout" type="button" data-logout>Выйти</button>';

    const logoutButton = container.querySelector('[data-logout]');
    if (logoutButton) {
      logoutButton.addEventListener('click', function () {
        api.clearSession();
        renderGuest();
      });
    }
  }

  function refresh() {
    if (api.getToken()) {
      const cached = api.getStoredUser();
      if (cached) {
        renderUser(cached);
      }
      api.me()
        .then(function (fresh) {
          api.saveSession({ access_token: api.getToken(), user: fresh });
          renderUser(fresh);
        })
        .catch(function (error) {
          // Токен действительно недействителен — сбрасываем сессию.
          if (error && error.code === 'unauthorized') {
            api.clearSession();
            renderGuest();
          } else if (!api.getStoredUser()) {
            // Временная ошибка сети и нет сохранённых данных — показываем гостя.
            renderGuest();
          }
        });
    } else {
      renderGuest();
    }
  }

  document.addEventListener('linguabot:auth-changed', refresh);
  refresh();
})();
