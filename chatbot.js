(function () {
  const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;

  const STORAGE_KEY = 'nebula_chat_history';
  const MSGS_KEY    = 'nebula_chat_msgs';

  // ── Inject styles ──────────────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #ns-fab {
      position: fixed; bottom: 28px; right: 28px; z-index: 9999;
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, #1a0050 0%, #006b57 100%);
      border: 2px solid rgba(21,255,209,0.4);
      box-shadow: 0 0 24px rgba(21,255,209,0.25), 0 4px 16px rgba(0,0,0,0.5);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
    }
    #ns-fab:hover { transform: scale(1.08); box-shadow: 0 0 36px rgba(21,255,209,0.4), 0 4px 20px rgba(0,0,0,0.6); }
    #ns-fab img { width: 28px; height: 28px; }

    #ns-chat-panel {
      position: fixed; bottom: 96px; right: 28px; z-index: 9998;
      width: 360px; max-height: 540px;
      background: rgba(5,14,31,0.97);
      backdrop-filter: blur(24px);
      border: 1px solid rgba(21,255,209,0.2);
      border-radius: 16px;
      box-shadow: 0 0 40px rgba(21,255,209,0.1), 0 16px 48px rgba(0,0,0,0.7);
      display: flex; flex-direction: column;
      transform: scale(0.9) translateY(20px); opacity: 0;
      pointer-events: none;
      transition: transform 0.2s ease, opacity 0.2s ease;
    }
    #ns-chat-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }

    #ns-chat-header {
      display: flex; align-items: center; gap: 10px;
      padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    #ns-chat-messages {
      flex: 1; overflow-y: auto; padding: 14px 16px;
      display: flex; flex-direction: column; gap: 12px;
      max-height: 360px; min-height: 200px;
    }
    #ns-chat-messages::-webkit-scrollbar { width: 4px; }
    #ns-chat-messages::-webkit-scrollbar-thumb { background: rgba(21,255,209,0.2); border-radius: 4px; }

    .ns-msg { max-width: 85%; font-size: 13px; line-height: 1.55; padding: 9px 13px; border-radius: 12px; word-break: break-word; }
    .ns-msg.user { background: rgba(21,255,209,0.12); color: #d4e4fa; border: 1px solid rgba(21,255,209,0.2); align-self: flex-end; border-bottom-right-radius: 4px; }
    .ns-msg.bot  { background: rgba(255,255,255,0.05); color: #b9cbc3; border: 1px solid rgba(255,255,255,0.08); align-self: flex-start; border-bottom-left-radius: 4px; }
    .ns-msg.bot strong { color: #15ffd1; }
    .ns-msg.error { background: rgba(255,100,100,0.1); color: #f87171; border: 1px solid rgba(255,100,100,0.2); align-self: flex-start; border-bottom-left-radius: 4px; }

    #ns-chat-input-row {
      display: flex; gap: 8px; padding: 12px 14px;
      border-top: 1px solid rgba(255,255,255,0.08);
    }
    #ns-chat-input {
      flex: 1; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px; padding: 9px 13px; color: #d4e4fa; font-size: 13px;
      outline: none; font-family: Inter, sans-serif; resize: none;
    }
    #ns-chat-input:focus { border-color: rgba(21,255,209,0.4); }
    #ns-send-btn {
      width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
      background: rgba(21,255,209,0.15); border: 1px solid rgba(21,255,209,0.3);
      color: #15ffd1; display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: background 0.15s;
    }
    #ns-send-btn:hover { background: rgba(21,255,209,0.25); }
    #ns-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    #ns-clear-btn {
      font-size: 11px; color: #64748b; background: none; border: none;
      cursor: pointer; padding: 2px 6px; border-radius: 6px;
      font-family: Inter, sans-serif; margin-left: 4px;
      transition: color 0.15s;
    }
    #ns-clear-btn:hover { color: #f87171; }

    .ns-typing { display: flex; gap: 4px; align-items: center; padding: 4px 0; }
    .ns-typing span { width: 6px; height: 6px; border-radius: 50%; background: #15ffd1; opacity: 0.4; animation: ns-bounce 1s infinite; }
    .ns-typing span:nth-child(2) { animation-delay: 0.15s; }
    .ns-typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes ns-bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px); opacity:1;} }

    @media (max-width: 480px) {
      #ns-chat-panel { width: calc(100vw - 32px); right: 16px; bottom: 88px; }
      #ns-fab { right: 16px; bottom: 16px; }
    }
  `;
  document.head.appendChild(style);

  // ── Inject HTML ────────────────────────────────────────────────────────────
  const root = document.createElement('div');
  root.innerHTML = `
    <button type="button" id="ns-fab" title="Ask NebulaAI">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L9.5 9.5H2L8 13.5L5.5 21L12 17L18.5 21L16 13.5L22 9.5H14.5L12 2Z" fill="#15ffd1" opacity="0.9"/>
      </svg>
    </button>

    <div id="ns-chat-panel">
      <div id="ns-chat-header">
        <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#1a0050,#006b57);border:1px solid rgba(21,255,209,0.3);display:flex;align-items:center;justify-content:center;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2L9.5 9.5H2L8 13.5L5.5 21L12 17L18.5 21L16 13.5L22 9.5H14.5L12 2Z" fill="#15ffd1"/></svg>
        </div>
        <div>
          <div style="color:white;font-size:14px;font-weight:700;font-family:'Space Grotesk',sans-serif;">NebulaAI</div>
          <div style="color:#15ffd1;font-size:11px;font-family:'Space Grotesk',sans-serif;">Powered by Google Gemini</div>
        </div>
        <button type="button" id="ns-clear-btn" title="Clear chat">Clear</button>
        <button type="button" id="ns-close-btn" style="color:#64748b;font-size:18px;background:none;border:none;cursor:pointer;line-height:1;">✕</button>
      </div>

      <div id="ns-chat-messages"></div>

      <div id="ns-chat-input-row">
        <textarea id="ns-chat-input" placeholder="Ask about crypto safety, scams, investing..." rows="1"></textarea>
        <button type="button" id="ns-send-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21L23 12 2 3v7l15 2-15 2z"/></svg>
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(root);

  // ── State ──────────────────────────────────────────────────────────────────
  const fab      = document.getElementById('ns-fab');
  const panel    = document.getElementById('ns-chat-panel');
  const closeBtn = document.getElementById('ns-close-btn');
  const clearBtn = document.getElementById('ns-clear-btn');
  const input    = document.getElementById('ns-chat-input');
  const sendBtn  = document.getElementById('ns-send-btn');
  const messages = document.getElementById('ns-chat-messages');

  // Load persisted conversation history (sent to Gemini) from sessionStorage
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]'); } catch(e) {}

  // Load persisted rendered messages from sessionStorage
  let savedMsgs = [];
  try { savedMsgs = JSON.parse(sessionStorage.getItem(MSGS_KEY) || '[]'); } catch(e) {}

  // ── Restore chat UI ────────────────────────────────────────────────────────
  function renderSaved() {
    messages.innerHTML = '';
    if (savedMsgs.length === 0) {
      // Show default greeting only when no history
      const div = document.createElement('div');
      div.className = 'ns-msg bot';
      div.innerHTML = `Hi! I'm <strong>NebulaAI</strong>, your crypto safety advisor powered by <strong>Google Gemini</strong>. 🌐<br><br>Ask me anything about crypto investing, scam detection, or how to stay safe in Web3.`;
      messages.appendChild(div);
    } else {
      savedMsgs.forEach(m => _renderMsg(m.text, m.type));
    }
    messages.scrollTop = messages.scrollHeight;
  }

  function _renderMsg(text, type) {
    const div = document.createElement('div');
    div.className = `ns-msg ${type}`;
    div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addMsg(text, type) {
    const div = _renderMsg(text, type);
    // Persist rendered message (skip typing indicators / errors from 503)
    if (type !== 'error') {
      savedMsgs.push({ text, type });
      // Keep last 40 rendered messages
      if (savedMsgs.length > 40) savedMsgs = savedMsgs.slice(-40);
      sessionStorage.setItem(MSGS_KEY, JSON.stringify(savedMsgs));
    }
    return div;
  }

  function saveHistory() {
    // Keep last 20 turns to avoid huge payloads
    if (history.length > 20) history = history.slice(-20);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  }

  function clearChat() {
    history = [];
    savedMsgs = [];
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(MSGS_KEY);
    renderSaved();
  }

  renderSaved();

  // ── Events ─────────────────────────────────────────────────────────────────
  fab.addEventListener('click', (e) => { e.preventDefault(); panel.classList.toggle('open'); });
  closeBtn.addEventListener('click', () => panel.classList.remove('open'));
  clearBtn.addEventListener('click', clearChat);

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener('click', send);

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 80) + 'px';
  });

  // ── Send ───────────────────────────────────────────────────────────────────
  function showTyping() {
    const div = document.createElement('div');
    div.className = 'ns-msg bot';
    div.id = 'ns-typing';
    div.innerHTML = '<div class="ns-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById('ns-typing');
    if (t) t.remove();
  }

  async function send() {
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;

    addMsg(text, 'user');
    history.push({ role: 'user', content: text });
    saveHistory();
    showTyping();

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history }),
        signal: AbortSignal.timeout(25000),
      });

      const data = await res.json();
      removeTyping();

      if (!res.ok) {
        const errText = data.detail || 'Something went wrong. Try again.';
        addMsg(errText, 'error');
      } else {
        addMsg(data.reply, 'bot');
        history.push({ role: 'assistant', content: data.reply });
        saveHistory();
      }
    } catch (err) {
      removeTyping();
      if (err.name === 'TimeoutError') {
        addMsg('NebulaAI took too long to respond. Try again.', 'error');
      } else {
        addMsg('Could not reach NebulaAI. Make sure the backend is running.', 'error');
      }
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }
})();
