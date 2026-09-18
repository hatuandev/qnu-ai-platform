/**
 * QNU AI Platform — Standalone Web Chat Widget
 * Trường Đại học Quy Nhơn (QNU)
 * 
 * Mã nhúng độc lập dành cho Cổng thông tin (qnu.edu.vn, tuyensinh.qnu.edu.vn, daotao.qnu.edu.vn)
 * Nhúng với 1 dòng script:
 * <script src="https://ai.qnu.edu.vn/embed/qnu-chat-widget.js" data-assistant="ast_admissions" defer></script>
 */

(function () {
  if (window.__QNU_CHAT_WIDGET_LOADED__) return;
  window.__QNU_CHAT_WIDGET_LOADED__ = true;

  // Lấy cấu hình từ thẻ script
  const scriptTag = document.currentScript || document.querySelector('script[src*="qnu-chat-widget"]');
  const ASSISTANT_ID = scriptTag?.getAttribute("data-assistant") || "ast_admissions";
  const WIDGET_TITLE = scriptTag?.getAttribute("data-title") || "Trợ lý AI ĐH Quy Nhơn";
  const WELCOME_MSG = scriptTag?.getAttribute("data-welcome") || "Xin chào! Tôi là Trợ lý AI của Trường Đại học Quy Nhơn. Tôi có thể hỗ trợ gì cho bạn hôm nay?";
  const POSITION = scriptTag?.getAttribute("data-position") || "bottom-right";
  const API_BASE = scriptTag?.getAttribute("data-api-base") || window.location.origin;

  // Khởi tạo container
  const container = document.createElement("div");
  container.id = "qnu-widget-root";
  document.body.appendChild(container);

  // Injected CSS Stylesheet (Scoped)
  const style = document.createElement("style");
  style.textContent = `
    #qnu-widget-root {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      z-index: 999999;
      position: fixed;
      bottom: 24px;
      ${POSITION === "bottom-left" ? "left: 24px;" : "right: 24px;"}
    }
    #qnu-widget-button {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: linear-gradient(135deg, #0f766e, #0d9488);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(15, 118, 110, 0.35);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border: 2px solid rgba(255, 255, 255, 0.2);
    }
    #qnu-widget-button:hover {
      transform: scale(1.06);
      box-shadow: 0 6px 24px rgba(15, 118, 110, 0.45);
    }
    #qnu-widget-button svg {
      width: 28px;
      height: 28px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
    }
    #qnu-widget-window {
      display: none;
      flex-direction: column;
      width: 380px;
      height: 560px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 100px);
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.16), 0 2px 10px rgba(0, 0, 0, 0.08);
      border: 1px solid #e2e8f0;
      position: absolute;
      bottom: 72px;
      ${POSITION === "bottom-left" ? "left: 0;" : "right: 0;"}
      overflow: hidden;
      animation: qnuWidgetPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes qnuWidgetPop {
      from { opacity: 0; transform: translateY(16px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    #qnu-widget-header {
      background: linear-gradient(135deg, #0f766e, #115e59);
      color: #ffffff;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .qnu-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .qnu-avatar {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
    }
    .qnu-header-title {
      font-weight: 600;
      font-size: 14px;
      line-height: 1.2;
    }
    .qnu-header-sub {
      font-size: 11px;
      opacity: 0.85;
    }
    #qnu-widget-close {
      background: none;
      border: none;
      color: #ffffff;
      cursor: pointer;
      padding: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      opacity: 0.8;
      transition: opacity 0.2s;
    }
    #qnu-widget-close:hover { opacity: 1; background: rgba(255, 255, 255, 0.1); }
    #qnu-widget-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f8fafc;
    }
    .qnu-msg {
      max-width: 84%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
      word-break: break-word;
    }
    .qnu-msg-user {
      align-self: flex-end;
      background: #0f766e;
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }
    .qnu-msg-bot {
      align-self: flex-start;
      background: #ffffff;
      color: #1e293b;
      border: 1px solid #e2e8f0;
      border-bottom-left-radius: 2px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .qnu-msg-bot table {
      border-collapse: collapse;
      width: 100%;
      margin: 8px 0;
      font-size: 12px;
    }
    .qnu-msg-bot th, .qnu-msg-bot td {
      border: 1px solid #cbd5e1;
      padding: 4px 8px;
    }
    .qnu-msg-bot th {
      background: #f1f5f9;
      font-weight: 600;
    }
    .qnu-citations-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-top: 6px;
      font-size: 11px;
      color: #0f766e;
      background: #ccfbf1;
      padding: 2px 6px;
      border-radius: 4px;
    }
    #qnu-widget-input-box {
      padding: 10px 12px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #qnu-widget-input {
      flex: 1;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }
    #qnu-widget-input:focus { border-color: #0f766e; }
    #qnu-widget-send {
      background: #0f766e;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.2s;
    }
    #qnu-widget-send:hover { background: #115e59; }
    #qnu-widget-send:disabled { background: #94a3b8; cursor: not-allowed; }
    .qnu-footer-tag {
      font-size: 10px;
      color: #94a3b8;
      text-align: center;
      padding: 4px 0 6px 0;
      background: #ffffff;
    }
  `;
  document.head.appendChild(style);

  // Injected HTML DOM
  container.innerHTML = `
    <div id="qnu-widget-window">
      <div id="qnu-widget-header">
        <div class="qnu-header-left">
          <div class="qnu-avatar">QNU</div>
          <div>
            <div class="qnu-header-title">${WIDGET_TITLE}</div>
            <div class="qnu-header-sub">Trường Đại học Quy Nhơn</div>
          </div>
        </div>
        <button id="qnu-widget-close" aria-label="Đóng chat">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div id="qnu-widget-messages">
        <div class="qnu-msg qnu-msg-bot">${WELCOME_MSG}</div>
      </div>
      <div id="qnu-widget-input-box">
        <input id="qnu-widget-input" type="text" placeholder="Nhập câu hỏi cần tư vấn..." />
        <button id="qnu-widget-send" aria-label="Gửi tin nhắn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
      <div class="qnu-footer-tag">QNU AI Platform • Zero-Hallucination</div>
    </div>
    <button id="qnu-widget-button" aria-label="Mở Trợ lý AI QNU">
      <svg viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    </button>
  `;

  // Các phần tử tương tác
  const btnToggle = document.getElementById("qnu-widget-button");
  const winChat = document.getElementById("qnu-widget-window");
  const btnClose = document.getElementById("qnu-widget-close");
  const boxMessages = document.getElementById("qnu-widget-messages");
  const inputMsg = document.getElementById("qnu-widget-input");
  const btnSend = document.getElementById("qnu-widget-send");

  let isOpen = false;
  let isStreaming = false;

  function toggleWidget() {
    isOpen = !isOpen;
    winChat.style.display = isOpen ? "flex" : "none";
    if (isOpen) {
      inputMsg.focus();
    }
  }

  btnToggle.addEventListener("click", toggleWidget);
  btnClose.addEventListener("click", toggleWidget);

  function appendMessage(text, isUser = false) {
    const el = document.createElement("div");
    el.className = `qnu-msg ${isUser ? "qnu-msg-user" : "qnu-msg-bot"}`;
    el.textContent = text;
    boxMessages.appendChild(el);
    boxMessages.scrollTop = boxMessages.scrollHeight;
    return el;
  }

  async function handleSend() {
    const question = inputMsg.value.trim();
    if (!question || isStreaming) return;

    inputMsg.value = "";
    appendMessage(question, true);

    const botMsgEl = appendMessage("Đang tra cứu cơ sở dữ liệu...", false);
    isStreaming = true;
    btnSend.disabled = true;

    try {
      const streamUrl = `${API_BASE}/platform/v1alpha1/assistants/${ASSISTANT_ID}/chat_stream`;
      const response = await fetch(streamUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      botMsgEl.textContent = "";
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullAnswer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.delta) {
                fullAnswer += data.delta;
                botMsgEl.textContent = fullAnswer;
                boxMessages.scrollTop = boxMessages.scrollHeight;
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      }

      if (!fullAnswer.trim()) {
        botMsgEl.textContent = "Không nhận được phản hồi từ trợ lý.";
      }
    } catch (err) {
      botMsgEl.textContent = "Có lỗi xảy ra khi kết nối tới máy chủ. Vui lòng thử lại sau.";
    } finally {
      isStreaming = false;
      btnSend.disabled = false;
      inputMsg.focus();
    }
  }

  btnSend.addEventListener("click", handleSend);
  inputMsg.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
})();
