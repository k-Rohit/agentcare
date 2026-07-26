/* ─────────── config (publishable values are safe in the browser) ─────────── */
const SUPABASE_URL = "https://dcolyqwmopwagieacudz.supabase.co";
const SUPABASE_KEY = "sb_publishable_T8kSr1aMtEi5c_0NvAqXmw_ibFRk13G";
const API_BASE = "/agentcare/api/v1";

/* ─────────── state ─────────── */
let token = localStorage.getItem("agentcare_token");
let conversationId = null;
let userName = "";

/* ─────────── elements ─────────── */
const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const authError = document.getElementById("auth-error");
const messagesEl = document.getElementById("messages");
const convListEl = document.getElementById("conversation-list");

/* ─────────── Supabase auth (frontend → Supabase directly) ─────────── */
async function supabaseLogin(email, password) {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error_description || data.msg || "Login failed");
  cacheName(data.user && data.user.user_metadata && data.user.user_metadata.full_name);
  return data.access_token;
}

async function supabaseSignup(name, email, password) {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, data: { full_name: name } }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error_description || data.msg || "Sign up failed");
  cacheName(name);
  return data; // has access_token only if email confirmation is disabled
}

/* ─────────── cached first name (for an instant greeting on load) ─────────── */
function cacheName(name) {
  if (name) localStorage.setItem("agentcare_name", name);
}

/* ─────────── backend API helper (adds the Bearer token) ─────────── */
async function api(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && (data.detail || data.message)) || "Request failed");
  return data;
}

/* ─────────── active conversation (persisted so reload keeps the chat) ─────────── */
function setConversation(id) {
  conversationId = id;
  if (id) localStorage.setItem("agentcare_conversation", id);
  else localStorage.removeItem("agentcare_conversation");
}

/* ─────────── view switching ─────────── */
async function showApp() {
  authView.classList.add("hidden");
  appView.classList.remove("hidden");

  // Paint from cache INSTANTLY — no network wait. Restore the last open chat if any.
  userName = localStorage.getItem("agentcare_name") || "";
  conversationId = localStorage.getItem("agentcare_conversation") || null;
  if (conversationId) openConversation(conversationId);
  else showGreeting();

  // Then reconcile with the server in the background.
  try {
    const me = await api("/me");
    userName = me.name || me.email || "";
    cacheName(me.name);
    document.getElementById("user-name").textContent = me.name || me.email || "You";
    document.getElementById("user-role").textContent = me.role || "";
    document.getElementById("user-avatar").textContent = (userName.trim()[0] || "?").toUpperCase();
  } catch { /* token invalid → logout already handled */ return; }

  // Only re-render the greeting if the real first name differs from what we showed
  // (and the patient hasn't started typing yet) — avoids any visible flicker.
  const realFirst = firstName(userName);
  if (!conversationId && realFirst !== greetedFirst && !messagesEl.querySelector(".msg.user")) {
    showGreeting();
  }
  loadConversations();
}

function firstName(name) {
  return name ? name.split(" ")[0] : "there";
}

let greetedFirst = "";
function showGreeting() {
  greetedFirst = firstName(userName);
  messagesEl.innerHTML = "";
  addMessage(
    "assistant",
    `Hi ${greetedFirst}! 👋 I'm your AgentCare assistant. I can help you book, reschedule, ` +
    `or cancel appointments, check your upcoming ones, or attach documents. ` +
    `What can I do for you today?`
  );
}

function showAuth() {
  appView.classList.add("hidden");
  authView.classList.remove("hidden");
}

function logout() {
  token = null;
  setConversation(null);
  greetedFirst = "";
  localStorage.removeItem("agentcare_token");
  localStorage.removeItem("agentcare_name");
  showAuth();
}

/* ─────────── auth form wiring ─────────── */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const isLogin = tab.dataset.tab === "login";
    document.getElementById("login-form").classList.toggle("hidden", !isLogin);
    document.getElementById("signup-form").classList.toggle("hidden", isLogin);
    authError.textContent = "";
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  authError.textContent = "";
  const f = e.target;
  try {
    token = await supabaseLogin(f.email.value, f.password.value);
    localStorage.setItem("agentcare_token", token);
    await showApp();
  } catch (err) { authError.textContent = err.message; }
});

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  authError.textContent = "";
  const f = e.target;
  try {
    const data = await supabaseSignup(f.name.value, f.email.value, f.password.value);
    if (data.access_token) {
      token = data.access_token;
      localStorage.setItem("agentcare_token", token);
      await showApp();
    } else {
      authError.style.color = "var(--good)";
      authError.textContent = "Account created — please confirm your email, then log in.";
    }
  } catch (err) { authError.style.color = ""; authError.textContent = err.message; }
});

/* ─────────── chat rendering ─────────── */
function clearEmptyState() {
  const es = messagesEl.querySelector(".empty-state");
  if (es) es.remove();
}
function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

/* tiny, safe markdown → HTML (bold, italic, code, numbered/bulleted lists) */
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inlineMd(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}
function renderMarkdown(text) {
  const lines = escapeHtml(text).split(/\n/);
  let html = "", list = null, items = [];
  const flush = () => {
    if (!list) return;
    html += `<${list}>` + items.map((it) =>
      `<li${it.value ? ` value="${it.value}"` : ""}>${it.parts.map(inlineMd).join("<br>")}</li>`
    ).join("") + `</${list}>`;
    items = []; list = null;
  };
  for (const line of lines) {
    const ol = line.match(/^\s*(\d+)[.)]\s+(.*)/);   // captures the number
    const ul = line.match(/^\s*[-*•]\s+(.*)/);
    if (ol) {
      if (list && list !== "ol") flush();
      list = "ol"; items.push({ value: ol[1], parts: [ol[2]] });
    } else if (ul && list !== "ol") {
      if (list && list !== "ul") flush();
      list = "ul"; items.push({ parts: [ul[1]] });
    } else if (line.trim() === "") {
      flush();
    } else if (list && items.length) {
      // a detail line under the current item (e.g. Date / Status / Reason, or a
      // sub-bullet under a numbered appointment) — keep it attached, don't split
      items[items.length - 1].parts.push((ul ? ul[1] : line).trim());
    } else {
      flush();
      html += `<p>${inlineMd(line)}</p>`;
    }
  }
  flush();
  return html;
}

/* build a message row (avatar + bubble). Assistant bubbles render markdown. */
function buildRow(role, extraClass = "") {
  clearEmptyState();
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;
  if (role === "assistant" || role === "user") {
    const av = document.createElement("div");
    av.className = role === "assistant" ? "avatar" : "avatar user";
    av.textContent = role === "assistant" ? "✚" : (userName.trim()[0] || "🙂").toUpperCase();
    row.appendChild(av);
  }
  const bubble = document.createElement("div");
  bubble.className = `msg ${role} ${extraClass}`.trim();
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  return bubble;
}

function addMessage(role, content, extraClass = "") {
  const bubble = buildRow(role, extraClass);
  if (role === "assistant") bubble.innerHTML = renderMarkdown(content);
  else bubble.innerHTML = escapeHtml(content).replace(/\n/g, "<br>");
  scrollToBottom();
  return bubble;
}

/* typewriter streaming for assistant replies */
function streamMessage(content, extraClass = "") {
  return new Promise((resolve) => {
    const bubble = buildRow("assistant", extraClass);
    const full = content || "";
    const step = Math.max(2, Math.round(full.length / 110)); // ~110 frames total
    let i = 0;
    const tick = () => {
      i = Math.min(full.length, i + step);
      bubble.innerHTML = renderMarkdown(full.slice(0, i)) + (i < full.length ? '<span class="caret"></span>' : "");
      scrollToBottom();
      if (i >= full.length) resolve(bubble);
      else setTimeout(tick, 16);
    };
    tick();
  });
}

let typingRow = null;
function showTyping() {
  clearEmptyState();
  typingRow = document.createElement("div");
  typingRow.className = "typing-row";
  typingRow.innerHTML = '<div class="avatar">✚</div><div class="typing"><span></span><span></span><span></span></div>';
  messagesEl.appendChild(typingRow);
  scrollToBottom();
}
function hideTyping() { if (typingRow) { typingRow.remove(); typingRow = null; } }

/* ─────────── slot selection (the interrupt) ─────────── */
function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}
function fmtDay(iso) {
  return new Date(iso).toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });
}

function renderSlots(options) {
  clearEmptyState();
  const wrap = document.createElement("div");
  wrap.className = "slots";
  const label = document.createElement("div");
  label.className = "slots-label";
  label.textContent = "Here are the available times — pick one:";
  wrap.appendChild(label);

  // sort chronologically, and show each time once (multiple doctors can have the
  // same slot time — the patient picks a time, whichever doctor is fine)
  const sorted = [...options].sort((a, b) => new Date(a.start) - new Date(b.start));
  const byDay = {};
  sorted.forEach((o) => { (byDay[fmtDay(o.start)] ||= []).push(o); });

  Object.entries(byDay).forEach(([day, opts]) => {
    const d = document.createElement("div");
    d.className = "slot-day";
    d.textContent = day;
    wrap.appendChild(d);
    const row = document.createElement("div");
    row.className = "slot-row";
    const seenTimes = new Set();
    opts.forEach((o) => {
      const time = fmtTime(o.start);
      if (seenTimes.has(time)) return;   // dedupe the repeated time
      seenTimes.add(time);
      const b = document.createElement("button");
      b.className = "slot-btn";
      b.textContent = time;
      b.addEventListener("click", () => {
        wrap.querySelectorAll(".slot-btn").forEach((x) => (x.disabled = true));
        const label = `${fmtDay(o.start)}, ${fmtTime(o.start)}`;
        addMessage("user", label);
        resume(o.slot_id, label);
      });
      row.appendChild(b);
    });
    wrap.appendChild(row);
  });

  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

/* ─────────── send / resume ─────────── */
async function handleResponse(resp) {
  setConversation(resp.conversation_id);
  hideTyping();
  if (resp.status === "awaiting_input" && resp.interrupt) {
    const note = resp.department_message
      || (resp.department ? `Sure — let's find you an opening in ${resp.department}. 🩺` : null);
    if (note) await streamMessage(note);
    renderSlots(resp.interrupt.options || []);
  } else if (resp.status === "escalated") {
    await streamMessage(resp.reply, "escalated");
  } else {
    await streamMessage(resp.reply || "Done.");
  }
  loadConversations();
}

async function sendMessage(text, attachment) {
  const shown = attachment ? `${text ? text + "\n" : ""}📎 ${attachment.filename}` : text;
  addMessage("user", shown);
  showTyping();
  try {
    const body = {
      message: text || `Please file this document: ${attachment.filename}`,
      conversation_id: conversationId,
    };
    if (attachment) {
      body.document_path = attachment.path;
      body.document_filename = attachment.filename;
    }
    const resp = await api("/chat", { method: "POST", body: JSON.stringify(body) });
    await handleResponse(resp);
  } catch (err) {
    hideTyping();
    addMessage("assistant", "Something went wrong: " + err.message);
  }
}

async function resume(slotId, label) {
  showTyping();
  try {
    const resp = await api("/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, resume_value: slotId, resume_label: label }),
    });
    await handleResponse(resp);
  } catch (err) {
    hideTyping();
    addMessage("assistant", "Something went wrong: " + err.message);
  }
}

/* ─────────── document attachment ─────────── */
let pendingAttachment = null;
const fileInput = document.getElementById("file-input");
const attachChip = document.getElementById("attach-chip");

async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  // multipart — let the browser set Content-Type (with boundary); don't use api()
  const res = await fetch(API_BASE + "/documents/upload", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  });
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.detail) || "Upload failed");
  return data; // { path, filename }
}

function renderAttachChip(name, uploading) {
  attachChip.classList.remove("hidden");
  attachChip.innerHTML = "";
  const label = document.createElement("span");
  label.textContent = (uploading ? "⏳ Uploading " : "📎 ") + name;
  attachChip.appendChild(label);
  if (!uploading) {
    const x = document.createElement("button");
    x.type = "button";
    x.className = "chip-remove";
    x.textContent = "✕";
    x.title = "Remove";
    x.addEventListener("click", clearAttachment);
    attachChip.appendChild(x);
  }
}
function clearAttachment() {
  pendingAttachment = null;
  attachChip.classList.add("hidden");
  attachChip.innerHTML = "";
}

document.getElementById("attach-btn").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  fileInput.value = "";  // let the same file be picked again later
  if (!file) return;
  renderAttachChip(file.name, true);
  try {
    pendingAttachment = await uploadFile(file);
    renderAttachChip(pendingAttachment.filename, false);
  } catch (err) {
    clearAttachment();
    addMessage("assistant", "Upload failed: " + err.message);
  }
});

/* ─────────── composer (auto-grow textarea, Enter to send) ─────────── */
const composerInput = document.getElementById("composer-input");
function autoGrow() {
  composerInput.style.height = "auto";
  composerInput.style.height = Math.min(composerInput.scrollHeight, 160) + "px";
}
function submitComposer() {
  const text = composerInput.value.trim();
  if (!text && !pendingAttachment) return;   // allow sending an attachment alone
  const attachment = pendingAttachment;
  composerInput.value = "";
  autoGrow();
  clearAttachment();
  sendMessage(text, attachment);
}
document.getElementById("composer").addEventListener("submit", (e) => { e.preventDefault(); submitComposer(); });
composerInput.addEventListener("input", autoGrow);
composerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitComposer(); }
});

document.querySelectorAll(".suggestion").forEach((s) => {
  s.addEventListener("click", () => sendMessage(s.textContent));
});

/* ─────────── conversations sidebar ─────────── */
async function loadConversations() {
  let convos = [];
  try { convos = await api("/conversations"); } catch { return; }
  convListEl.innerHTML = "";
  convos.forEach((c) => {
    const row = document.createElement("div");
    row.className = "conversation-item" + (c.id === conversationId ? " active" : "");
    const summary = (c.state && c.state.summary) || "(conversation)";

    const label = document.createElement("span");
    label.className = "conv-label";
    label.textContent = summary;
    label.title = summary;
    label.addEventListener("click", () => openConversation(c.id));

    const del = document.createElement("button");
    del.className = "conv-delete";
    del.textContent = "🗑";
    del.title = "Delete conversation";
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(c.id);
    });

    row.appendChild(label);
    row.appendChild(del);
    convListEl.appendChild(row);
  });
}

async function deleteConversation(id) {
  try {
    await api(`/conversations/${id}`, { method: "DELETE" });
  } catch (err) {
    return; // leave the sidebar as-is if the delete failed
  }
  if (conversationId === id) {
    setConversation(null);
    showGreeting();
  }
  loadConversations();
}

async function openConversation(id) {
  setConversation(id);
  messagesEl.innerHTML = "";
  try {
    const msgs = await api(`/conversations/${id}/messages`);
    msgs.forEach((m) => addMessage(m.role === "user" ? "user" : "assistant", m.content));
  } catch {
    addMessage("status", "(Couldn't load this conversation's messages.)");
  }
  loadConversations();
}

document.getElementById("new-chat").addEventListener("click", () => {
  setConversation(null);
  showGreeting();
  loadConversations();
});

document.getElementById("logout").addEventListener("click", logout);

/* ─────────── boot ─────────── */
if (token) { showApp(); } else { showAuth(); }
