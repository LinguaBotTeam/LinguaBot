(function () {
  const api = window.LinguaBotAPI;
  const root = document.querySelector('[data-chat]');
  if (!api || !root) return;

  const find = (name) => root.querySelector('[data-chat-' + name + ']');
  const auth = find('auth');
  const workspace = find('workspace');
  const create = find('create');
  const list = find('dialogues');
  const listEmpty = find('list-empty');
  const name = find('name');
  const scenario = find('scenario');
  const thread = find('thread');
  const empty = find('empty');
  const messages = find('messages');
  const status = find('status');
  const errorBox = find('error');
  const reload = find('reload');
  const form = find('form');
  const example = find('example');
  const input = form.elements.content;
  const send = find('send');

  const topicNames = {
    cafe: 'В кафе',
    introductions: 'Знакомство',
    shop: 'В магазине',
    free_chat: 'Свободный разговор',
  };
  const dateFormat = new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
  const pageSize = 100;

  let dialogues = [];
  let active = null;
  let historyReady = false;
  let busy = false;
  let generation = 0;

  function formatDate(value) {
    if (!value) return '';
    const date = new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : value + 'Z');
    return Number.isNaN(date.getTime()) ? '' : dateFormat.format(date);
  }

  function syncControls() {
    create.disabled = busy;
    reload.disabled = busy;
    list.querySelectorAll('button').forEach((button) => { button.disabled = busy; });
    form.hidden = !active || !historyReady;
    input.disabled = busy;
    send.disabled = busy || !input.value.trim();
    example.disabled = busy;
  }

  function setStatus(message) {
    busy = Boolean(message);
    status.textContent = message;
    syncControls();
  }

  function setError(message, canReload = false) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
    reload.hidden = !message || !canReload;
  }

  function renderDialogues() {
    list.replaceChildren();
    listEmpty.hidden = dialogues.length > 0;
    dialogues.forEach((dialogue) => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      const label = document.createElement('strong');
      const date = document.createElement('span');
      button.className = 'chat-dialogue';
      button.type = 'button';
      if (active && dialogue.id === active.id) button.setAttribute('aria-current', 'true');
      label.textContent = dialogue.title;
      date.className = 'chat-muted';
      date.textContent = formatDate(dialogue.created_at);
      button.append(label, date);
      button.addEventListener('click', () => {
        run('Загружаем историю…', (current) => openDialogue(dialogue, current), true);
      });
      item.append(button);
      list.append(item);
    });
    syncControls();
  }

  function setActive(dialogue) {
    active = dialogue;
    historyReady = false;
    name.textContent = dialogue ? dialogue.title : 'В кафе';
    const topic = dialogue && Object.hasOwn(topicNames, dialogue.scenario)
      ? topicNames[dialogue.scenario]
      : 'Текстовый диалог';
    scenario.textContent = topic + ' · Английский';
    messages.replaceChildren();
    empty.hidden = false;
    empty.textContent = dialogue
      ? 'Напишите первое сообщение, чтобы начать разговор.'
      : 'Создайте диалог или выберите сохранённый.';
    input.value = '';
    example.hidden = !dialogue || dialogue.scenario !== 'cafe';
    renderDialogues();
  }

  function appendMessage(message) {
    const item = document.createElement('li');
    item.className = 'chat-message' + (message.role === 'user' ? ' is-user' : '');
    const speaker = document.createElement('p');
    speaker.className = 'chat-speaker';
    speaker.textContent = message.role === 'user' ? 'Вы' : 'LinguaBot';
    const content = document.createElement('p');
    content.className = 'chat-message-text';
    content.lang = 'en';
    content.textContent = message.content;
    item.append(speaker, content);
    if (message.correction) {
      const correction = document.createElement('p');
      correction.className = 'chat-correction';
      correction.textContent = message.correction;
      item.append(correction);
    }
    messages.append(item);
    empty.hidden = true;
    example.hidden = true;
  }

  function scrollToLatest() {
    thread.scrollTop = thread.scrollHeight;
  }

  async function readPages(request, isCurrent) {
    const items = new Map();
    let offset = 0;
    while (isCurrent()) {
      const page = await request(pageSize, offset);
      if (!isCurrent()) break;
      if (!Array.isArray(page)) throw new Error('Сервер вернул неожиданный ответ.');
      page.forEach((item) => items.set(item.id, item));
      if (page.length < pageSize) break;
      offset += page.length;
    }
    return Array.from(items.values());
  }

  async function openDialogue(dialogue, isCurrent) {
    setActive(dialogue);
    const history = await readPages(
      (limit, offset) => api.getDialogueMessages(dialogue.id, limit, offset), isCurrent,
    );
    if (!isCurrent()) return;
    history.forEach(appendMessage);
    historyReady = true;
    syncControls();
    scrollToLatest();
    const url = new URL(window.location.href);
    url.searchParams.set('dialogue', String(dialogue.id));
    window.history.replaceState(null, '', url);
  }

  async function run(message, action, canReload = false) {
    if (busy) return;
    const token = api.getToken();
    if (!token) {
      refresh();
      return;
    }
    const version = ++generation;
    const isCurrent = () => version === generation && token === api.getToken();
    setError('');
    setStatus(message);
    try {
      await action(isCurrent);
    } catch (error) {
      if (isCurrent() && error.code === 'unauthorized') {
        api.clearSession();
        document.dispatchEvent(new CustomEvent('linguabot:auth-changed'));
      } else if (isCurrent()) {
        setError(error.message || 'Не удалось выполнить запрос.', canReload);
      }
    } finally {
      if (isCurrent()) {
        setStatus('');
      } else if (version === generation) {
        refresh();
      }
    }
  }

  function refresh() {
    generation += 1;
    const signedIn = Boolean(api.getToken());
    auth.hidden = signedIn;
    workspace.hidden = !signedIn;
    dialogues = [];
    setStatus('');
    setError('');
    setActive(null);
    if (!signedIn) return;

    run('Загружаем диалоги…', async (isCurrent) => {
      const items = await readPages(api.listDialogues, isCurrent);
      if (!isCurrent()) return;
      dialogues = items;
      renderDialogues();
      const requested = new URLSearchParams(window.location.search).get('dialogue');
      const selected = dialogues.find((item) => String(item.id) === requested) || dialogues[0];
      if (selected) await openDialogue(selected, isCurrent);
    }, true);
  }

  create.addEventListener('click', () => {
    run('Создаём диалог…', async (isCurrent) => {
      const dialogue = await api.createDialogue('В кафе', 'cafe');
      if (!isCurrent()) return;
      dialogues.unshift(dialogue);
      await openDialogue(dialogue, isCurrent);
    }, true);
  });
  reload.addEventListener('click', refresh);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const content = input.value.trim();
    if (!active || !historyReady || !content || content.length > 4000) return;
    const dialogueId = active.id;
    run('LinguaBot готовит ответ…', async (isCurrent) => {
      const pair = await api.sendDialogueMessage(dialogueId, content);
      if (!isCurrent()) return;
      appendMessage(pair.user_message);
      appendMessage(pair.assistant_message);
      input.value = '';
      scrollToLatest();
    }).then(() => {
      if (!workspace.hidden && active && active.id === dialogueId && !input.disabled) {
        input.focus();
      }
    });
  });
  input.addEventListener('input', syncControls);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      if (!send.disabled) form.requestSubmit();
    }
  });
  example.addEventListener('click', () => {
    input.value = 'I would like a tea, please.';
    syncControls();
    input.focus();
  });
  root.querySelectorAll('[data-chat-auth-mode]').forEach((button) => {
    button.addEventListener('click', () => window.LinguaBotAuth.open(button.dataset.chatAuthMode));
  });
  document.addEventListener('linguabot:auth-changed', refresh);
  refresh();
})();
