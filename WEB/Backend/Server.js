const express = require("express");
const fs = require("fs");
const cors = require("cors");
const bodyParser = require("body-parser");

const multer = require("multer");
const upload = multer({ dest: "uploads/" });

const app = express();
const PORT = 8001;

app.use(cors());
app.use(bodyParser.json());

// Хранилище файлов для RAG
let knowledgeBase = [];

// -----------------------------
// Работа с БД (файл Database.json)
// -----------------------------
function loadDB() {
    if (!fs.existsSync("Database.json")) {
        fs.writeFileSync("Database.json", JSON.stringify({ chats: [] }, null, 2));
    }
    return JSON.parse(fs.readFileSync("Database.json", "utf8"));
}

function saveDB(data) {
    fs.writeFileSync("Database.json", JSON.stringify(data, null, 2));
}

// -----------------------------
// Получить список чатов
// -----------------------------
app.get("/chats", (req, res) => {
    const db = loadDB();
    res.json(db.chats);
});

// -----------------------------
// Создать новый чат
// -----------------------------
app.post("/chats", (req, res) => {
    const db = loadDB();

    const now = new Date().toISOString();

    const newChat = {
        id: Date.now(),
        title: req.body?.title || "Новый чат",
        created_at: now,
        updated_at: now,
        messages: []
    };

    db.chats.push(newChat);
    saveDB(db);

    res.json(newChat);
});


// -----------------------------
// Получить весь чат целиком
// — это то, что вызывается фронтом loadChatMessages()
// -----------------------------
app.get("/chats/:id", (req, res) => {
    const db = loadDB();
    const chat = db.chats.find(c => c.id == req.params.id);

    if (!chat) return res.status(404).json({ error: "Chat not found" });

    res.json({
        id: chat.id,
        title: chat.title,
        created_at: chat.created_at,
        updated_at: chat.updated_at,
        messages: chat.messages
    });
});

// -----------------------------
// Получить сообщения чата (если нужно отдельно)
// -----------------------------
app.get("/chats/:id/messages", (req, res) => {
    const db = loadDB();
    const chat = db.chats.find(c => c.id == req.params.id);

    if (!chat) return res.status(404).json({ error: "Chat not found" });

    res.json(chat.messages);
});

// -----------------------------
// Добавить сообщение в чат
// -----------------------------
app.post("/chats/:id/messages", (req, res) => {
    const db = loadDB();
    const chat = db.chats.find(c => c.id == req.params.id);

    if (!chat) return res.status(404).json({ error: "Chat not found" });

    const msg = {
        id: Date.now(),
        role: req.body.role || "user",
        text: req.body.text,
        time: new Date().toISOString()
    };

    chat.messages.push(msg);
    chat.updated_at = msg.time;   // ← обновление времени чата
    saveDB(db);

    res.json(msg);
});

app.delete("/chats/:id", (req, res) => {
    const db = loadDB();
    db.chats = db.chats.filter(c => c.id != req.params.id);
    saveDB(db);
    res.json({ ok: true });
});

// -----------------------------
// Переименовать чат
// -----------------------------
app.patch("/chats/:id", (req, res) => {
    const db = loadDB();
    const chat = db.chats.find(c => c.id == req.params.id);

    if (!chat) return res.status(404).json({ error: "Chat not found" });

    chat.title = req.body.title ?? chat.title;

    saveDB(db);
    res.json(chat);
});

// -----------------------------
// INGEST — загрузка файлов для знания
// -----------------------------
app.post("/ingest", upload.array("files"), (req, res) => {
    req.files.forEach(f => {
        knowledgeBase.push({
            file: f.originalname,
            path: f.path
        });
    });

    res.json({
        status: "ok",
        uploaded: req.files.length
    });
});

// -----------------------------
// RAG — тестовый ответ
// -----------------------------
app.post("/rag/query", (req, res) => {
    const query = req.body.query;

    const fakeAnswer = `Тестовый ответ для запроса: "${query}"`;
    const fakeSources = knowledgeBase.slice(0, 3).map(f => ({
        score: Math.random(),
        file: f.file,
        page: 1,
        text: "Пример текста источника..."
    }));

    res.json({
        answer: fakeAnswer,
        sources: fakeSources
    });
});

// -----------------------------
app.listen(PORT, () =>
    console.log("Backend запущен на http://localhost:" + PORT)
);