(function () {
  const API_BASE = window.LINGUABOT_API_URL || 'http://127.0.0.1:8000/api/v1';
  const TOKEN_KEY = 'linguabot-token';
  const USER_KEY = 'linguabot-user';

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  }

  function getStoredUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveSession(payload) {
    try {
      localStorage.setItem(TOKEN_KEY, payload.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
    } catch {
      // Сессия не сохраняется, если браузер запрещает localStorage.
    }
  }

  function clearSession() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      // Ничего страшного: данных для удаления нет.
    }
  }

  // Сервер отдаёт ошибки в формате { error: { code, message, field } }.
  function toError(data, status) {
    if (data && data.error && typeof data.error === 'object') {
      const error = new Error(data.error.message || 'Произошла ошибка.');
      error.code = data.error.code || null;
      error.field = data.error.field || null;
      return error;
    }
    if (data && typeof data.detail === 'string') {
      return new Error(data.detail);
    }
    if (data && Array.isArray(data.detail) && data.detail.length > 0) {
      return new Error(data.detail[0].msg || 'Проверьте введённые данные.');
    }
    if (status === 422) {
      return new Error('Данные отсутствуют или имеют неверный формат.');
    }
    return new Error('Произошла ошибка. Попробуйте ещё раз.');
  }

  async function request(path, options) {
    const config = options || {};
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) {
      headers.Authorization = 'Bearer ' + token;
    }

    let response;
    try {
      response = await fetch(API_BASE + path, {
        method: config.method || 'GET',
        headers: headers,
        body: config.body,
      });
    } catch {
      throw new Error('Не удалось связаться с сервером. Убедитесь, что он запущен.');
    }

    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }

    if (!response.ok) {
      throw toError(data, response.status);
    }
    return data;
  }

  window.LinguaBotAPI = {
    // Регистрация: возвращает объект пользователя (id, name, email), без токена.
    register: function (name, email, password) {
      return request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name: name, email: email, password: password }),
      });
    },
    // Вход: возвращает { access_token, token_type, expires_in, user }.
    login: function (email, password) {
      return request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: email, password: password }),
      });
    },
    me: function () {
      return request('/auth/me', { method: 'GET' });
    },
    getToken: getToken,
    getStoredUser: getStoredUser,
    saveSession: saveSession,
    clearSession: clearSession,
  };
})();
