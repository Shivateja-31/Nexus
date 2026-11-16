// NexusCLI Agent Frontend Client
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("prompt-input");
  const sendBtn = document.getElementById("send-btn");
  const messagesContainer = document.getElementById("messages-container");
  const executionBanner = document.getElementById("execution-banner");
  const executionBannerText = document.getElementById("execution-banner-text");
  const executionBannerTool = document.getElementById("execution-banner-tool");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const sidebar = document.getElementById("sidebar");
  const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");

  let isExecuting = false;

  // Auto-resize textarea
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
  });

  // Enter to submit (Shift+Enter for newline)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isExecuting && input.value.trim()) {
        form.dispatchEvent(new Event("submit"));
      }
    }
  });

  // Toggle mobile sidebar
  if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener("click", () => {
      sidebar.classList.toggle("-translate-x-full");
    });
  }

  // Clear chat button
  clearChatBtn.addEventListener("click", () => {
    if (confirm("Clear all messages in the chat session?")) {
      messagesContainer.innerHTML = "";
      addSystemNotification("Chat session cleared. Ready for new commands.");
    }
  });

  // Preset buttons handler
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt && !isExecuting) {
        input.value = prompt;
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 150) + "px";
        form.dispatchEvent(new Event("submit"));
        if (window.innerWidth < 768 && sidebar) {
          sidebar.classList.add("-translate-x-full");
        }
      }
    });
  });

  // Form submit handler
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = input.value.trim();
    if (!prompt || isExecuting) return;

    // Reset input
    input.value = "";
    input.style.height = "auto";
    setLoadingState(true);

    // Append user message
    appendUserMessage(prompt);

    // Create assistant message container with live stream
    const assistantCard = createAssistantCard();
    messagesContainer.appendChild(assistantCard.element);
    scrollToBottom();

    try {
      await executeWithStreaming(prompt, assistantCard);
    } catch (err) {
      console.warn("Streaming encountered error, falling back to standard REST:", err);
      try {
        await executeWithRest(prompt, assistantCard);
      } catch (restErr) {
        assistantCard.setError("Network or Server error: " + restErr.message);
      }
    } finally {
      setLoadingState(false);
      scrollToBottom();
    }
  });

  function setLoadingState(loading) {
    isExecuting = loading;
    sendBtn.disabled = loading;
    if (loading) {
      executionBanner.classList.remove("hidden");
    } else {
      executionBanner.classList.add("hidden");
    }
  }

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "flex justify-end animate-fade-in";
    div.innerHTML = `
      <div class="max-w-2xl bg-brand-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-md text-sm leading-relaxed">
        <p class="whitespace-pre-wrap">${escapeHtml(text)}</p>
      </div>
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
  }

  function addSystemNotification(text) {
    const div = document.createElement("div");
    div.className = "text-center my-3 text-xs text-slate-500";
    div.innerText = text;
    messagesContainer.appendChild(div);
  }

  function createAssistantCard() {
    const cardId = "card-" + Math.random().toString(36).substring(2, 9);
    const div = document.createElement("div");
    div.className = "flex gap-3 max-w-4xl animate-fade-in";
    div.id = cardId;

    div.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0 text-brand-400 mt-1 shadow-sm">
        <i data-lucide="bot" class="w-4 h-4"></i>
      </div>
      <div class="flex-1 space-y-3 overflow-hidden">
        <!-- Status & Stepper Badge -->
        <div class="status-bar flex items-center gap-2 text-xs text-slate-400">
          <span class="status-indicator flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 font-mono text-[11px]">
            <i data-lucide="loader" class="w-3 h-3 animate-spin"></i>
            <span class="status-text">Interpreting intent...</span>
          </span>
          <span class="tool-tag hidden px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]"></span>
        </div>

        <!-- Terminal Execution Drawer (Collapsible) -->
        <div class="terminal-drawer rounded-lg overflow-hidden border border-slate-800 bg-[#050811] shadow-lg">
          <div class="terminal-toggle flex items-center justify-between px-3 py-1.5 bg-slate-900/90 border-b border-slate-800 cursor-pointer hover:bg-slate-800/80 transition text-xs select-none">
            <div class="flex items-center gap-2">
              <i data-lucide="terminal" class="w-3.5 h-3.5 text-brand-400"></i>
              <span class="font-mono text-[11px] text-slate-300 terminal-cmd-title">Subprocess Terminal Inspector</span>
            </div>
            <div class="flex items-center gap-2 text-slate-400">
              <span class="process-meta-badge font-mono text-[10px] text-slate-400">PID: ...</span>
              <i data-lucide="chevron-down" class="w-3.5 h-3.5 transition-transform duration-200 toggle-icon"></i>
            </div>
          </div>
          <div class="terminal-content">
            <pre class="terminal-body font-mono text-[11px] p-3 max-h-56 overflow-y-auto text-slate-300 bg-[#050811] leading-relaxed"></pre>
          </div>
        </div>

        <!-- Markdown Summary Section -->
        <div class="markdown-container prose-custom text-sm text-slate-200"></div>

        <!-- Structured JSON Block (Collapsible with Copy Button) -->
        <div class="json-container hidden rounded-lg border border-slate-800 bg-slate-900/80 overflow-hidden shadow-md">
          <div class="flex items-center justify-between px-3 py-2 bg-slate-800/70 border-b border-slate-700/60 text-xs">
            <div class="flex items-center gap-1.5 font-medium text-slate-300">
              <i data-lucide="braces" class="w-3.5 h-3.5 text-cyan-400"></i>
              <span>Structured Output (JSON)</span>
            </div>
            <div class="flex items-center gap-2">
              <button class="copy-json-btn px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 flex items-center gap-1 transition text-[11px]">
                <i data-lucide="copy" class="w-3 h-3"></i>
                <span class="copy-text">Copy JSON</span>
              </button>
              <button class="download-json-btn px-2 py-0.5 rounded bg-brand-600/80 hover:bg-brand-500 text-white flex items-center gap-1 transition text-[11px]">
                <i data-lucide="download" class="w-3 h-3"></i>
                <span>Download</span>
              </button>
            </div>
          </div>
          <pre class="json-body p-3 font-mono text-[11px] text-cyan-200/90 max-h-72 overflow-y-auto bg-slate-950/80"></pre>
        </div>

      </div>
    `;

    // Elements
    const terminalToggle = div.querySelector(".terminal-toggle");
    const terminalContent = div.querySelector(".terminal-content");
    const toggleIcon = div.querySelector(".toggle-icon");
    const terminalBody = div.querySelector(".terminal-body");
    const terminalCmdTitle = div.querySelector(".terminal-cmd-title");
    const processMetaBadge = div.querySelector(".process-meta-badge");
    const statusText = div.querySelector(".status-text");
    const statusIndicator = div.querySelector(".status-indicator");
    const toolTag = div.querySelector(".tool-tag");
    const markdownContainer = div.querySelector(".markdown-container");
    const jsonContainer = div.querySelector(".json-container");
    const jsonBody = div.querySelector(".json-body");
    const copyJsonBtn = div.querySelector(".copy-json-btn");
    const downloadJsonBtn = div.querySelector(".download-json-btn");

    // Drawer toggle
    let isDrawerOpen = true;
    terminalToggle.addEventListener("click", () => {
      isDrawerOpen = !isDrawerOpen;
      terminalContent.classList.toggle("hidden", !isDrawerOpen);
      toggleIcon.style.transform = isDrawerOpen ? "rotate(0deg)" : "rotate(-90deg)";
    });

    let currentJsonData = null;

    // Copy JSON action
    copyJsonBtn.addEventListener("click", () => {
      if (currentJsonData) {
        navigator.clipboard.writeText(JSON.stringify(currentJsonData, null, 2)).then(() => {
          const txt = copyJsonBtn.querySelector(".copy-text");
          txt.innerText = "Copied!";
          setTimeout(() => (txt.innerText = "Copy JSON"), 2000);
        });
      }
    });

    // Download JSON action
    downloadJsonBtn.addEventListener("click", () => {
      if (currentJsonData) {
        const blob = new Blob([JSON.stringify(currentJsonData, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `crawl-result-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    });

    lucide.createIcons({ root: div });

    return {
      element: div,
      appendTerminalLog(text) {
        terminalBody.textContent += text;
        terminalBody.scrollTop = terminalBody.scrollHeight;
      },
      setStatus(text, type = "loading") {
        statusText.innerText = text;
        if (type === "loading") {
          statusIndicator.className = "status-indicator flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 font-mono text-[11px]";
        } else if (type === "success") {
          statusIndicator.className = "status-indicator flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[11px]";
          statusIndicator.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span>${text}</span>`;
          lucide.createIcons({ root: statusIndicator });
        } else if (type === "error") {
          statusIndicator.className = "status-indicator flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 font-mono text-[11px]";
          statusIndicator.innerHTML = `<i data-lucide="alert-triangle" class="w-3 h-3 text-rose-400"></i><span>${text}</span>`;
          lucide.createIcons({ root: statusIndicator });
        }
      },
      setToolInfo(toolName, cmdLine, pid = null, duration = null) {
        toolTag.innerText = toolName;
        toolTag.classList.remove("hidden");
        terminalCmdTitle.innerText = `$ ${cmdLine}`;
        if (pid) {
          processMetaBadge.innerText = `PID: ${pid} | ${duration ? duration + "s" : ""}`;
        }
      },
      setSummary(markdown) {
        markdownContainer.innerHTML = renderMarkdown(markdown);
      },
      setJson(data) {
        if (!data) return;
        currentJsonData = data;
        jsonContainer.classList.remove("hidden");
        jsonBody.textContent = JSON.stringify(data, null, 2);
      },
      setError(message) {
        this.setStatus("Execution Failed", "error");
        markdownContainer.innerHTML = `<div class="p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs font-mono"><strong>Error:</strong> ${escapeHtml(message)}</div>`;
      }
    };
  }

  // Execute using streaming SSE
  async function executeWithStreaming(prompt, card) {
    executionBannerText.innerText = "Interpreting intent and invoking CLI...";
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: prompt })
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep remainder

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.substring(6).trim();
          if (!jsonStr) continue;
          try {
            const data = JSON.parse(jsonStr);
            handleStreamEvent(data, card);
          } catch (e) {
            console.error("SSE parse error:", e, jsonStr);
          }
        }
      }
    }
  }

  function handleStreamEvent(data, card) {
    switch (data.event) {
      case "start":
        card.setStatus("Analyzing request intent...");
        break;

      case "intent_parsed":
        const intent = data.intent;
        if (intent.tool_name) {
          card.setStatus(`Selected Tool: ${intent.tool_name}`);
          card.setToolInfo(intent.tool_name, `${intent.tool_name} ${intent.cli_args.join(" ")}`);
          card.appendTerminalLog(`[Intent Engine] Parsed intent -> Tool: ${intent.tool_name}\n[Intent Engine] Arguments: ${intent.cli_args.join(" ")}\n`);
        }
        break;

      case "security_passed":
        card.setStatus("Security Guard: SSRF cleared");
        card.appendTerminalLog(`[Security] Target validated -> ${data.url} (Resolved IP: ${data.resolved_ip || "Public DNS"})\n[Security] SSRF verification: PASS\n\n`);
        break;

      case "cli_started":
        card.setStatus(`Running: ${data.tool}...`);
        executionBannerText.innerText = `Executing: ${data.command}`;
        executionBannerTool.innerText = data.tool;
        card.appendTerminalLog(`$ ${data.command}\n`);
        break;

      case "cli_log":
        card.appendTerminalLog(data.line);
        break;

      case "completed":
        const resp = data.response;
        if (resp.success) {
          card.setStatus("Execution Completed (Exit Code: 0)", "success");
        } else {
          card.setStatus(resp.status === "security_blocked" ? "Security Blocked" : "Execution Failed", "error");
        }

        if (resp.execution_meta) {
          const meta = resp.execution_meta;
          card.setToolInfo(
            meta.tool_name || "CLI",
            meta.command || "",
            meta.pid,
            meta.duration_seconds
          );
        }

        if (resp.summary_markdown) {
          card.setSummary(resp.summary_markdown);
        }

        if (resp.structured_json) {
          card.setJson(resp.structured_json);
        }
        break;
    }
    scrollToBottom();
  }

  // Fallback REST execution
  async function executeWithRest(prompt, card) {
    card.setStatus("Executing CLI tool via REST...");
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: prompt })
    });
    const data = await res.json();
    if (data.terminal_logs) {
      card.appendTerminalLog(data.terminal_logs);
    }
    if (data.execution_meta) {
      const meta = data.execution_meta;
      card.setToolInfo(meta.tool_name || "CLI", meta.command || "", meta.pid, meta.duration_seconds);
    }
    if (data.success) {
      card.setStatus("Execution Completed", "success");
    } else {
      card.setStatus("Execution Failed", "error");
    }
    if (data.summary_markdown) {
      card.setSummary(data.summary_markdown);
    }
    if (data.structured_json) {
      card.setJson(data.structured_json);
    }
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Lightweight Markdown Renderer
  function renderMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Headings
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^## (.*$)/gim, "<h2 class='text-base font-bold text-white mt-3 mb-2'>$1</h2>");
    html = html.replace(/^# (.*$)/gim, "<h1 class='text-lg font-bold text-white mt-4 mb-2'>$1</h1>");

    // Blockquotes
    html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

    // Bold & Italic
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong class='font-semibold text-white'>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Inline Code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Bullet Lists
    html = html.replace(/^\- (.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>[\s\S]*?<\/li>)/gim, "<ul>$1</ul>");

    // Line breaks
    html = html.replace(/\n\n/g, "<p class='mt-2'></p>");
    html = html.replace(/\n/g, "<br />");

    return html;
  }
});
