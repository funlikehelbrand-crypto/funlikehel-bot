(function () {
  const API_URL = "https://funlikehel-bot.onrender.com/api/chat"; // TODO: zmien na produkcyjny URL
  let sessionId = localStorage.getItem("flh_session") || crypto.randomUUID();
  localStorage.setItem("flh_session", sessionId);
  let isOpen = false;

  // CSS
  const style = document.createElement("style");
  style.textContent = `
    #flh-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 60px; height: 60px; border-radius: 50%;
      background: #0073e6; color: #fff; border: none; cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,.3); font-size: 28px;
      display: flex; align-items: center; justify-content: center;
      transition: transform .2s;
    }
    #flh-chat-btn:hover { transform: scale(1.1); }
    #flh-chat-box {
      position: fixed; bottom: 96px; right: 24px; z-index: 99999;
      width: 370px; max-width: calc(100vw - 32px); height: 500px; max-height: 70vh;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,.2);
      display: none; flex-direction: column; overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    #flh-chat-box.open { display: flex; }
    #flh-chat-header {
      background: #0073e6; color: #fff; padding: 16px 20px;
      font-size: 16px; font-weight: 600; display: flex;
      align-items: center; gap: 10px;
    }
    #flh-chat-header .avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: rgba(255,255,255,.2); display: flex;
      align-items: center; justify-content: center; font-size: 18px;
    }
    #flh-chat-header .info { flex: 1; }
    #flh-chat-header .info small { opacity: .8; font-weight: 400; font-size: 12px; display: block; }
    #flh-chat-close {
      background: none; border: none; color: #fff; font-size: 22px;
      cursor: pointer; padding: 4px;
    }
    #flh-chat-msgs {
      flex: 1; overflow-y: auto; padding: 16px; display: flex;
      flex-direction: column; gap: 10px;
    }
    .flh-msg {
      max-width: 85%; padding: 10px 14px; border-radius: 16px;
      font-size: 14px; line-height: 1.5; word-wrap: break-word;
    }
    .flh-msg.bot {
      background: #f0f0f0; color: #333; align-self: flex-start;
      border-bottom-left-radius: 4px;
    }
    .flh-msg.user {
      background: #0073e6; color: #fff; align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .flh-msg.typing { font-style: italic; opacity: .6; }
    #flh-chat-input-wrap {
      padding: 12px 16px; border-top: 1px solid #eee;
      display: flex; gap: 8px;
    }
    #flh-chat-input {
      flex: 1; border: 1px solid #ddd; border-radius: 24px;
      padding: 10px 16px; font-size: 14px; outline: none;
      font-family: inherit;
    }
    #flh-chat-input:focus { border-color: #0073e6; }
    #flh-chat-send {
      background: #0073e6; color: #fff; border: none;
      border-radius: 50%; width: 40px; height: 40px; cursor: pointer;
      font-size: 18px; display: flex; align-items: center; justify-content: center;
    }
    #flh-chat-send:disabled { opacity: .5; cursor: not-allowed; }
  `;
  document.head.appendChild(style);

  // HTML
  const btn = document.createElement("button");
  btn.id = "flh-chat-btn";
  btn.innerHTML = "💬";
  btn.title = "Porozmawiaj z Alicja";
  document.body.appendChild(btn);

  const box = document.createElement("div");
  box.id = "flh-chat-box";
  box.innerHTML = `
    <div id="flh-chat-header">
      <div class="avatar">👩</div>
      <div class="info">Alicja<small>FUN like HEL</small></div>
      <button id="flh-chat-close">&times;</button>
    </div>
    <div id="flh-chat-msgs"></div>
    <div id="flh-chat-input-wrap">
      <input id="flh-chat-input" placeholder="Napisz wiadomosc..." autocomplete="off" />
      <button id="flh-chat-send">&#9654;</button>
    </div>
  `;
  document.body.appendChild(box);

  const msgs = box.querySelector("#flh-chat-msgs");
  const input = box.querySelector("#flh-chat-input");
  const sendBtn = box.querySelector("#flh-chat-send");

  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = "flh-msg " + who;
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function openChat() {
    isOpen = true;
    box.classList.add("open");
    if (msgs.children.length === 0) {
      addMsg("Hej! Jestem Alicja z FUN like HEL 🏄 Czym moge Ci pomoc? Pytaj o kursy, obozy, Egipt — cokolwiek!", "bot");
    }
    input.focus();
  }

  function closeChat() {
    isOpen = false;
    box.classList.remove("open");
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    addMsg(text, "user");
    sendBtn.disabled = true;

    const typing = addMsg("Alicja pisze...", "bot typing");

    try {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      typing.remove();

      if (resp.ok) {
        const data = await resp.json();
        addMsg(data.reply, "bot");
        sessionId = data.session_id;
        localStorage.setItem("flh_session", sessionId);
      } else {
        addMsg("Przepraszam, cos poszlo nie tak. Zadzwon: 690 270 032", "bot");
      }
    } catch (e) {
      typing.remove();
      addMsg("Brak polaczenia. Zadzwon: 690 270 032", "bot");
    }

    sendBtn.disabled = false;
    input.focus();
  }

  // Events
  btn.addEventListener("click", () => (isOpen ? closeChat() : openChat()));
  box.querySelector("#flh-chat-close").addEventListener("click", closeChat);
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();
