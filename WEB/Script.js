let currentChatId = null;
const chatListElem = document.getElementById("chatList");
const newChatBtn = document.getElementById("newChatBtn");

async function loadChatList() {
  const resp = await fetch(`${API_URL}/chats`);
  const chats = await resp.json();

  chatListElem.innerHTML = "";

  chats.sort((a, b) => b.updated_at - a.updated_at);

  chats.forEach(chat => {
    const div = document.createElement("div");
    div.className = "chat-item";
    div.dataset.id = chat.id;

    if (chat.id === currentChatId) div.classList.add("active");

    const title = document.createElement("span");
    title.className = "chat-title";
    title.textContent = chat.title || "Новый чат";

    title.onclick = (e) => {
      e.stopPropagation();
      enterEditMode(chat, title);
    };

    div.appendChild(title);

    div.onclick = () => openChat(chat.id);

    chatListElem.appendChild(div);
  });
}

newChatBtn.addEventListener("click", async () => {
  const resp = await fetch(`${API_URL}/chats`, { method: "POST" });
  const chat = await resp.json();

  currentChatId = chat.id;

  document.querySelectorAll(".chat-item").forEach(i =>
    i.classList.remove("active")
  );

  const div = document.createElement("div");
  div.className = "chat-item active";
  div.dataset.id = chat.id;

  const title = document.createElement("span");
  title.className = "chat-title";
  title.textContent = chat.title;

  title.onclick = (e) => {
    e.stopPropagation();
    enterEditMode(chat, title);
  };

  div.appendChild(title);
  div.onclick = () => openChat(chat.id);

  chatListElem.prepend(div);

  loadChatMessages(chat.id);
});

async function openChat(id) {
  currentChatId = id;

  document.querySelectorAll(".chat-item").forEach(item => {
    item.classList.remove("active");
  });

  const active = document.querySelector(`.chat-item[data-id="${id}"]`);
  if (active) active.classList.add("active");

  await loadChatMessages(id);
}

async function loadChatMessages(chatId) {
  chatHistory.innerHTML = "";

  const resp = await fetch(`${API_URL}/chats/${chatId}`);
  const data = await resp.json();

  console.log("hello?: ", data)

  data.messages.forEach(msg => addMessage(msg.role, msg.text));
}

window.onload = () => {
  loadChatList();
};


















const API_URL = "http://localhost:8001";  // поменяйте при деплое

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadStatus = document.getElementById("uploadStatus");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");
const chatHistory = document.getElementById("chatHistory");

let selectedFiles = [];

// Drag & drop
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", () => handleFiles(fileInput.files));

function handleFiles(files) {
  selectedFiles = Array.from(files);
  dropZone.innerHTML = `<p>Выбрано файлов: ${selectedFiles.length}</p>`;
  uploadBtn.disabled = false;
}

// Загрузка файлов
uploadBtn.addEventListener("click", async () => {
  if (selectedFiles.length === 0) return;

  uploadStatus.textContent = "Загружается...";
  uploadBtn.disabled = true;

  const formData = new FormData();
  selectedFiles.forEach((file, i) => formData.append("files", file));

  try {
    const resp = await fetch(`${API_URL}/ingest`, {
      method: "POST",
      body: formData
    });
    if (resp.ok) {
      uploadStatus.innerHTML = "База знаний успешно загружена!";
      selectedFiles = [];
      dropZone.innerHTML = "<p>Перетащите новые файлы или кликните</p>";
    } else {
      uploadStatus.textContent = "Ошибка загрузки";
    }
  } catch (e) {
    uploadStatus.textContent = "Нет связи с сервером";
  }
  uploadBtn.disabled = false;
});

// Отправка вопроса
sendBtn.addEventListener("click", sendQuestion);
questionInput.addEventListener("keypress", e => e.key === "Enter" && !e.shiftKey && sendQuestion());

async function sendQuestion() {
  if (!currentChatId) {
    alert("Сначала создайте или выберите чат!");
    return;
  }

  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";

  addMessage("assistant", "Думаю...");

  try {
    // 1 — сохранить сообщение пользователя в чате
    await fetch(`${API_URL}/chats/${currentChatId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "user", text: question })
    });

    // 2 — получить ответ RAG
    const resp = await fetch(`${API_URL}/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question })
    });
    const data = await resp.json();

    // удалить "Думаю..."
    chatHistory.lastElementChild.remove();

    // 3 — сохранить ответ ИИ в чат
    await fetch(`${API_URL}/chats/${currentChatId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "assistant", text: data.answer })
    });

    addMessage("assistant", data.answer, data.sources || []);
  } catch (err) {
    chatHistory.lastElementChild.remove();
    addMessage("assistant", "Ошибка связи с сервером");
  }
}

function addMessage(sender, text, sources = []) {
  console.log("test message: `{text}`")
  const div = document.createElement("div");
  div.className = `message ${sender}`;

  // Поддержка Markdown (простая)
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\n/g, '<br>');

  div.innerHTML = text;

  // Добавляем источники
  if (sources.length > 0) {
    const srcDiv = document.createElement("div");
    srcDiv.className = "sources";
    srcDiv.innerHTML = "<strong>Источники:</strong>";
    sources.forEach(src => {
      const s = document.createElement("div");
      s.className = "source-item";
      s.innerHTML = `
        <strong>Релевантность: ${(src.score*100).toFixed(1)}%</strong><br>
        ${src.file ? src.file + (src.page ? ` (стр. ${src.page})` : "") + "<br>" : ""}
        <em>${src.text.substring(0, 300)}...</em>
      `;
      srcDiv.appendChild(s);
    });
    div.appendChild(srcDiv);
  }

  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}







function renderChatList(chats) {
    const list = document.getElementById("chat-list");
    list.innerHTML = "";

    chats.forEach(chat => {
        const item = document.createElement("div");
        item.className = "chat-item";

        const title = document.createElement("span");
        title.textContent = chat.title;
        title.className = "chat-title";

        // При клике — переход в режим редактирования
        title.onclick = () => enterEditMode(chat, title);

        item.appendChild(title);
        list.appendChild(item);
    });
}

function enterEditMode(chat, titleElement) {
    const input = document.createElement("input");
    input.type = "text";
    input.value = chat.title;
    input.className = "chat-title-input";

    titleElement.replaceWith(input);
    input.focus();

    // Сохранить на Enter
    input.addEventListener("keydown", async e => {
        if (e.key === "Enter") {
            await renameChat(chat.id, input.value);
        }
        if (e.key === "Escape") {
            exitEditMode(chat, input);
        }
    });

    // Сохранение при потере фокуса
    input.addEventListener("blur", async () => {
        await renameChat(chat.id, input.value);
    });
}

function exitEditMode(chat, input) {
    const title = document.createElement("span");
    title.textContent = chat.title;
    title.className = "chat-title";
    title.onclick = () => enterEditMode(chat, title);

    input.replaceWith(title);
}

async function renameChat(id, newTitle) {
    await fetch(`http://localhost:8001/chats/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle })
    });

    // Обновляем список чатов
    await loadChatList();
}