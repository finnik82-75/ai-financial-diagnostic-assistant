document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll(".nav-link, .btn-brand[href^='#']");

    links.forEach((link) => {
        link.addEventListener("click", (event) => {
            const targetId = link.getAttribute("href");
            if (!targetId || !targetId.startsWith("#")) return;
            const target = document.querySelector(targetId);
            if (!target) return;

            event.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });

    const chatRoot = document.getElementById("ai-chat-widget");
    if (!chatRoot) return;

    const panel = document.getElementById("ai-chat-panel");
    const toggleBtn = document.getElementById("ai-chat-toggle");
    const closeBtn = document.getElementById("ai-chat-close");
    const messagesEl = document.getElementById("ai-chat-messages");
    const inputEl = document.getElementById("ai-chat-input");
    const sendBtn = document.getElementById("ai-chat-send");
    const chatUrl = chatRoot.dataset.chatUrl || "http://72.56.241.226:8000/chat";

    const scrollMessagesDown = () => {
        messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "smooth" });
    };

    const escapeHtml = (s) => {
        const d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    };

    /**
     * Форматирует ответ ассистента: абзацы, переносы строк, простые маркированные/нумерованные списки.
     * Текст экранируется (без доверия к HTML от API).
     */
    const formatAssistantHtml = (text) => {
        const raw = typeof text === "string" ? text.trim() : "";
        if (!raw) return "<p></p>";

        const blocks = raw.split(/\n\n+/);
        const htmlParts = [];

        for (const block of blocks) {
            const lines = block.split("\n");
            const trimmedLines = lines.map((l) => l.trimEnd());
            const nonEmpty = trimmedLines.map((l) => l.trim()).filter(Boolean);

            const bulletLike = (line) =>
                /^[-•*]\s/.test(line) || /^\d+[.)]\s/.test(line);

            const isList =
                nonEmpty.length > 0 && nonEmpty.every((l) => bulletLike(l));

            if (isList) {
                const ordered = /^\d+[.)]\s/.test(nonEmpty[0]);
                const tag = ordered ? "ol" : "ul";
                const items = nonEmpty
                    .map((l) => {
                        const inner = l.replace(/^[-•*]\s/, "").replace(/^\d+[.)]\s/, "");
                        return `<li>${escapeHtml(inner)}</li>`;
                    })
                    .join("");
                htmlParts.push(`<${tag}>${items}</${tag}>`);
            } else {
                const inner = trimmedLines
                    .map((line) => escapeHtml(line))
                    .join("<br>");
                htmlParts.push(`<p>${inner}</p>`);
            }
        }

        return htmlParts.join("");
    };

    const appendMsg = (text, role) => {
        const wrap = document.createElement("div");
        wrap.className = `ai-chat-msg ai-chat-msg--${role} ai-chat-msg--appear`;
        const bubble = document.createElement("div");
        bubble.className = "ai-chat-bubble";

        if (role === "assistant") {
            bubble.classList.add("ai-chat-bubble--rich");
            const inner = document.createElement("div");
            inner.className = "ai-chat-bubble-content";
            inner.innerHTML = formatAssistantHtml(text);
            bubble.appendChild(inner);
        } else {
            bubble.textContent = text;
        }

        wrap.appendChild(bubble);
        messagesEl.appendChild(wrap);
        scrollMessagesDown();
    };

    const setThinking = (show) => {
        const existing = messagesEl.querySelector(".ai-chat-msg--thinking");
        if (show) {
            if (existing) return;
            const wrap = document.createElement("div");
            wrap.className =
                "ai-chat-msg ai-chat-msg--assistant ai-chat-msg--thinking ai-chat-msg--appear";
            const bubble = document.createElement("div");
            bubble.className = "ai-chat-bubble";
            bubble.textContent = "Ассистент думает...";
            wrap.appendChild(bubble);
            messagesEl.appendChild(wrap);
            scrollMessagesDown();
        } else if (existing) {
            existing.remove();
        }
    };

    const openPanel = () => {
        panel.classList.add("is-visible");
        panel.setAttribute("aria-hidden", "false");
        toggleBtn.setAttribute("aria-expanded", "true");
        requestAnimationFrame(() => {
            inputEl.focus();
            scrollMessagesDown();
        });
    };

    const closePanel = () => {
        panel.classList.remove("is-visible");
        panel.setAttribute("aria-hidden", "true");
        toggleBtn.setAttribute("aria-expanded", "false");
    };

    toggleBtn.addEventListener("click", () => {
        if (!panel.classList.contains("is-visible")) openPanel();
        else closePanel();
    });

    closeBtn.addEventListener("click", () => closePanel());

    let sending = false;

    const sendMessage = async () => {
        const text = inputEl.value.trim();
        if (!text || sending) return;

        sending = true;
        appendMsg(text, "user");
        inputEl.value = "";
        setThinking(true);
        sendBtn.disabled = true;

        try {
            const res = await fetch(chatUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            if (!res.ok) throw new Error("bad status");

            const data = await res.json();
            const answer =
                data && typeof data.answer === "string" ? data.answer : null;
            if (!answer) throw new Error("no answer");

            setThinking(false);
            appendMsg(answer, "assistant");
        } catch {
            setThinking(false);
            appendMsg(
                "Ассистент временно недоступен. Попробуйте позже или оставьте заявку.",
                "assistant",
            );
        } finally {
            sending = false;
            sendBtn.disabled = false;
            scrollMessagesDown();
        }
    };

    sendBtn.addEventListener("click", sendMessage);

    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendMessage();
        }
    });
});
