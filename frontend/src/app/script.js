const root = document.documentElement;
const themeToggle = document.querySelector('#theme-toggle');
const themeIcon = document.querySelector('#theme-icon');
const themeLabel = document.querySelector('#theme-label');

function applyTheme(theme) {
  root.dataset.theme = theme;
  const isDark = theme === 'dark';
  themeIcon.textContent = isDark ? '☀' : '☾';
  themeLabel.textContent = isDark ? 'Светлая тема' : 'Тёмная тема';
  themeToggle.setAttribute('aria-label',
    isDark ? 'Включить светлую тему' : 'Включить тёмную тему');
}

applyTheme(root.dataset.theme === 'light' ? 'light' : 'dark');

themeToggle.addEventListener('click', () => {
  const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(theme);
  try {
    localStorage.setItem('linguabot-theme', theme);
  } catch {
    // Переключение работает даже при запрете сохранения в браузере.
  }
});

const startNotice = document.querySelector('#start-notice');

document.querySelectorAll('[data-start]').forEach((button) => {
  button.addEventListener('click', () => {
    startNotice.showModal();
  });
});
