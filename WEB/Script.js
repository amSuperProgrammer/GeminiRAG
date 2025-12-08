// const socket = io("https://agent.memphis.netcraze.pro", {
//   path: "/socket.io/"
// });

// socket.on("connect", () => {
//   console.log("Rasa connected");
// });






const newChatBtn = document.getElementById('newChatBtn');
const chatList = document.getElementById('chatList');
const chatHistory = document.getElementById('chatHistory');
const sendBtn = document.getElementById('sendBtn');
const question = document.getElementById('question');

let currentChatIndex = null;


// --- Создание чата ---
async function createChat() {
    const body = {
        v0Name: "Новый чат",
        v0ModelIndex: 0
    };

    const response = await fetch("http://localhost:8000/Chats/Creates/V0Post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    if (!response.ok) return;

    const chat = await response.json();
    addChatToSidebar(chat);
    selectChatByIndex(chat.v0ChatIndex);
}

function addChatToSidebar(chat) {
    const item = document.createElement('div');
    item.classList.add('chat-item');
    item.dataset.index = chat.v0ChatIndex;

    const title = document.createElement('div');
    title.className = 'chat-title';
    title.textContent = chat.v0Name;

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    meta.innerHTML = `
        <span>Создан: ${new Date(chat.v0DateTimeRegister).toLocaleTimeString()}</span>
        <span>Обновлён: ${new Date(chat.v0DateTimeUpdate).toLocaleTimeString()}</span>
    `;

    const actions = document.createElement('div');
    actions.className = 'chat-actions';

    // --- кнопка редактирования ---
    const btnEdit = document.createElement('button');
    btnEdit.className = 'chat-btn';
    btnEdit.innerHTML = "✎";
    btnEdit.addEventListener('click', async (e) => {
        e.stopPropagation(); // не переключаем чат

        // Текущее имя чата
        const oldName = title.textContent;

        // Ввод нового имени
        const newName = prompt("Введите новое имя чата:", oldName);
        if (!newName || newName.trim() === "" || newName === oldName) return;

        // API: обновление имени
        await fetch("http://localhost:8000/Chats/Updates/V0Post", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                V0ChatIndex: chat.v0ChatIndex,
                V0UserIndex: 0,
                V0Name: newName,
                V0ModelIndex: chat.v0ModelIndex ?? 0
            })
        });

        // Визуальное обновление
        title.textContent = newName;
        console.log("Имя изменено:", newName);
    });

    // --- кнопка удаления ---
    const btnDelete = document.createElement('button');
    btnDelete.className = 'chat-btn';
    btnDelete.innerHTML = "✕";
    btnDelete.addEventListener('click', async (e) => {
        e.stopPropagation(); // не переключаем чат

        const index = chat.v0ChatIndex;

        // API запрос на удаление
        await fetch("http://localhost:8000/Chats/Deletes/V0Post", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                V0ChatIndex: index,
                V0UserIndex: 0
            })
        });

        console.log("Удалён:", index);

        // удаляем элемент из DOM
        item.remove();

        // если удалён выбранный чат – переключаемся
        if (currentChatIndex === index) {
            const items = [...chatList.children];
            if (items.length > 0) {
                const firstAvailable = +items[0].dataset.index;
                selectChatByIndex(firstAvailable);
            } else {
                currentChatIndex = null;
                chatHistory.innerHTML = "";
            }
        }
    });



    actions.appendChild(btnEdit);
    actions.appendChild(btnDelete);

    item.appendChild(title);
    item.appendChild(meta);
    item.appendChild(actions);

    // --- кликаем по блоку → выбираем чат ---
    item.addEventListener('click', () => {
        selectChatByIndex(chat.v0ChatIndex);
    });

    chatList.appendChild(item);
}


// --- Выбор чата ---
function selectChatByIndex(index) {
    currentChatIndex = index;

    document.querySelectorAll('.chat-item')
        .forEach(e => e.classList.remove('active'));

    const selected = [...chatList.children]
        .find(e => e.dataset.index == index);

    if (selected) selected.classList.add('active');

    chatHistory.innerHTML = "";
    loadMessages(index);
}


// --- Загрузка сообщений ---
async function loadMessages(chatIndex) {
    const body = {
        V0ChatIndex: chatIndex,
        V0UserIndex: 0,
        V0Message: ""
    };

    const response = await fetch("http://localhost:8000/Chats/Messages/V0Get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    if (!response.ok) return;

    const data = await response.json();
    const targetChat = data.find(c => c.v0ChatIndex === chatIndex);
    if (!targetChat || !targetChat.v0Messages) return;

    chatHistory.innerHTML = "";

    targetChat.v0Messages.forEach(m => {
        addMessageToUI(
            m.v0Content,
            m.v0UserIndex === 0 ? "user" : "bot"
        );
    });
}


// --- UI сообщение ---
function addMessageToUI(text, type = "user") {
    const msg = document.createElement("div");
    msg.className = "message " + type;
    msg.textContent = text;
    chatHistory.appendChild(msg);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}


// --- API отправка ---
async function sendMessageToServer(text, userIndex) {
    const body = {
        V0ChatIndex: currentChatIndex,
        V0UserIndex: userIndex,
        V0Message: text
    };

    await fetch("http://localhost:8000/Chats/Sends/V0Post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
}

// New function.
async function sendMessageToRasa(message) {
    const userId = crypto.randomUUID();
    // const response = await fetch('https://agent.memphis.netcraze.pro/webhooks/rest/webhook', {
    const response = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            //sender: 'unique-user-id', // For session tracking
            sender: userId, // Store this ID in localStorage/cookies so it persists across page reloads.
            message: message
        })
    });
    const data = await response.json();
    // data is an array of bot responses, e.g., [{ "text": "Bot reply" }]
    return data;
}

// --- Отправка сообщения ---
async function handleSend() {
    const text = question.value.trim();
    //if (!text || currentChatIndex === null) return;

    question.value = "";

    // пользовательское сообщение
    // addMessageToUI(text, "user");
    // await sendMessageToServer(text, 0);

    // // ответ модели (тест)
    // setTimeout(async () => {
    //     const botReply = "💡 Ответ модели";
    //     addMessageToUI(botReply, "bot");
    //     await sendMessageToServer(botReply, 1);
    // }, 400);
    
    addMessageToUI(text, "user");

    // Usage: Integrate with your chat UI
    await sendMessageToRasa(text).then(responses => {
        responses.forEach(resp => { 
            addMessageToUI(resp.text, "bot")
            console.log(resp.text)
        });
    });
}

// загрузка всех чатов
async function loadAllChats() {
    chatList.innerHTML = "";

    const response = await fetch("http://localhost:8000/Chats/Fulls/V0Get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            V0ChatIndex: -1, // запрос списка всех чатов
            V0UserIndex: 0,
            V0Message: ""
        })
    });

    if (!response.ok) return;

    const chats = await response.json();
    if (!Array.isArray(chats)) return;

    chats.forEach(c => addChatToSidebar(c));

    if (chats.length > 0) {
        selectChatByIndex(chats[0].v0ChatIndex);
    } else {
        currentChatIndex = null;
        chatHistory.innerHTML = "";
    }
}

// --- События ---
newChatBtn.addEventListener('click', createChat);
sendBtn.addEventListener('click', handleSend);
question.addEventListener('keydown', e => {
    if (e.key === "Enter") handleSend();
});

window.addEventListener("DOMContentLoaded", () => {
    loadAllChats();
});


















socket.on("bot_uttered", async (response) => {
    const reply = response.text || "";

    console.log("answer: ", reply)

    addMessageToUI(reply, "bot");
    await sendMessageToServer(reply, 1);
});





































///////// ПОЛНАЯ РАБОТА С ЗАГРУЗКОЙ КНОПКИ

const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadStatus = document.getElementById("uploadStatus");
const dropZone = document.getElementById("dropZone");

let selectedFiles = [];

// --- Активируем кнопку, когда выбраны файлы ---
fileInput.addEventListener("change", () => {
    selectedFiles = [...fileInput.files];
    uploadBtn.disabled = selectedFiles.length === 0;
});

// --- Drag & Drop для удобства ---
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    selectedFiles = [...e.dataTransfer.files];
    fileInput.files = e.dataTransfer.files;
    uploadBtn.disabled = selectedFiles.length === 0;
});


// --- Загрузка в базу ---
uploadBtn.addEventListener("click", async () => {
    if (selectedFiles.length === 0) return;

    uploadBtn.disabled = true;
    uploadStatus.innerText = "⏳ Загружается…";

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append("files", f));

    try {
        const response = await fetch("http://localhost:8000/Knowledge/Upload", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Ошибка API");

        uploadStatus.innerText = "✅ Файлы загружены в базу!";
        fileInput.value = "";
        selectedFiles = [];
    } catch (err) {
        uploadStatus.innerText = "❌ Ошибка загрузки";
        console.error(err);
    } finally {
        uploadBtn.disabled = true;
    }
});
