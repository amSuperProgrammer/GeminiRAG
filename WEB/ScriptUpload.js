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

    // const formData = new FormData();
    // selectedFiles.forEach(f => formData.append("files", f));

    for (const file of selectedFiles) {
        // 1) extract
        let fd = new FormData()
        fd.append("file", file)

        const extractResp = await fetch("http://localhost:8004/extract", {
            method: "POST",
            body: fd
        })
        const extracted = await extractResp.json()

        // 2) chunks
        const chunksResp = await fetch("http://localhost:8005/chunks_get", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                text: extracted.text,
                title: extracted.filename,
                chunk_size: 1200,
                overlap: 250
            })
        })
        const docs = await chunksResp.json()

        // 3) ingest
        await fetch("http://localhost:8000/ingest", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(docs)
        })
    }

    try {
        // const response = await fetch("http://localhost:8000/Knowledge/Upload", {
        //     method: "POST",
        //     body: formData
        // });

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
