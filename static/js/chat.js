(function () {
  const API_BASE = window.__API_BASE__ || "http://localhost:8000";

  const launcher = document.getElementById("chat-launcher");
  const widget = document.getElementById("chat-widget");
  const closeBtn = document.getElementById("chat-close");
  const messagesEl = document.getElementById("chat-messages");
  const inputEl = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  let isSending = false;

  function appendMessage(text, from) {
    const div = document.createElement("div");
    div.className = "chat-message " + from;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendTyping() {
    const div = document.createElement("div");
    div.className = "chat-message bot";
    div.id = "typing-indicator";
    div.innerHTML =
      '<div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
  }

  async function sendMessage() {
    if (isSending) return;
    const text = inputEl.value.trim();
    if (!text) return;

    appendMessage(text, "user");
    inputEl.value = "";

    isSending = true;
    sendBtn.disabled = true;
    appendTyping();

    try {
      const res = await fetch(API_BASE + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, top_k: 3 }),
      });

      if (!res.ok) {
        throw new Error("Server error");
      }

      const data = await res.json();
      removeTyping();
      appendMessage(data.answer, "bot");
    } catch (err) {
      console.error(err);
      removeTyping();
      appendMessage("Не удалось получить ответ. Проверьте, что FastAPI запущен.", "bot");
    } finally {
      isSending = false;
      sendBtn.disabled = false;
    }
  }

  launcher.addEventListener("click", () => {
    widget.style.display = "flex";
    launcher.style.display = "none";
    if (!messagesEl.hasChildNodes()) {
      appendMessage(
        "Привет! Я помогаю разобраться в прибыли, расходах и денежных потоках. Задайте вопрос по управленческой отчётности.",
        "bot"
      );
    }
    setTimeout(() => inputEl.focus(), 50);
  });

  closeBtn.addEventListener("click", () => {
    widget.style.display = "none";
    launcher.style.display = "flex";
  });

  sendBtn.addEventListener("click", sendMessage);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();
