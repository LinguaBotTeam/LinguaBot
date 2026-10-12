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
      '<a class="nav-link" href="./login.html">Войти</a>' +
      '<a class="button button-sm" href="./register.html">Регистрация</a>';
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
      .catch(function () {
        api.clearSession();
        renderGuest();
      });
  } else {
    renderGuest();
  }
})();
