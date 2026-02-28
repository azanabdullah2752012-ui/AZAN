/* ── AZAN AI Frontend — Chat Logic ─────────────────────────────── */

const API_BASE = window.location.origin;
const messagesArea = document.getElementById('messagesArea');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const welcomeScreen = document.getElementById('welcomeScreen');
const clearChat = document.getElementById('clearChat');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

let isProcessing = false;

// ── Initialize ──────────────────────────────────────────────────

window.addEventListener('load', () => {
    chatInput.focus();
    loadStatus();
    loadKnowledge();
    // Refresh status every 30s
    setInterval(loadStatus, 30000);
});

// ── Status Check ────────────────────────────────────────────────

async function loadStatus() {
    try {
        const resp = await fetch(`${API_BASE}/api/status`);
        const data = await resp.json();

        const dot = document.getElementById('statusDot');
        const ollamaEl = document.getElementById('ollamaStatus');
        const modelEl = document.getElementById('modelStatus');
        const inferenceEl = document.getElementById('inferenceStatus');

        if (data.ollama && data.ollama.online) {
            dot.className = 'panel-dot online';
            ollamaEl.textContent = 'Online';
            ollamaEl.className = 'status-value online';

            const models = data.ollama.models || [];
            const primary = models.find(m => m.startsWith('llama3:')) || models[0] || '—';
            modelEl.textContent = primary.split(':')[0];
        } else {
            dot.className = 'panel-dot offline';
            ollamaEl.textContent = 'Offline';
            ollamaEl.className = 'status-value offline';
            modelEl.textContent = '—';
        }

        inferenceEl.textContent = data.rl_inference ? 'RL + KB' : 'Direct';
        inferenceEl.className = 'status-value' + (data.rl_inference ? ' online' : '');
    } catch (e) {
        console.error('Status check failed:', e);
        document.getElementById('statusDot').className = 'panel-dot offline';
        document.getElementById('ollamaStatus').textContent = 'Error';
        document.getElementById('ollamaStatus').className = 'status-value offline';
    }
}

// ── Knowledge Stats ─────────────────────────────────────────────

async function loadKnowledge() {
    try {
        const resp = await fetch(`${API_BASE}/api/knowledge`);
        const data = await resp.json();

        document.getElementById('articleCount').textContent = data.total_articles || 0;
        document.getElementById('trainingCount').textContent = data.total_training_pairs || 0;

        const categories = data.categories || [];
        document.getElementById('categoryCount').textContent = categories.length;

        const chipsContainer = document.getElementById('categoryChips');
        chipsContainer.innerHTML = categories
            .slice(0, 8)
            .map(c => `<span class="category-chip">${escapeHtml(c)}</span>`)
            .join('');
    } catch (e) {
        console.error('Knowledge load failed:', e);
    }
}

// ── Chat ────────────────────────────────────────────────────────

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;

    // Hide welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // Add user message
    addMessage(text, 'user');
    chatInput.value = '';
    autoResize();

    // Show typing indicator
    const typingEl = showTyping();

    try {
        const resp = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text })
        });

        typingEl.remove();

        if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

        const data = await resp.json();
        const aiText = data.response || 'Sorry, I could not generate a response.';
        const source = data.source || 'unknown';

        addMessage(aiText, 'ai', source);
    } catch (err) {
        typingEl.remove();
        console.error('Chat error:', err);
        addMessage('Error: Could not connect to the server. Make sure the backend is running.', 'ai', 'error');
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

function sendSuggestion(text) {
    chatInput.value = text;
    sendMessage();
}

// ── Message Rendering ───────────────────────────────────────────

function addMessage(text, sender, source) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;

    const senderLabel = document.createElement('div');
    senderLabel.className = 'message-sender';
    senderLabel.textContent = sender === 'user' ? 'You' : 'AZAN AI';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = formatMessage(text);

    msgDiv.appendChild(senderLabel);
    msgDiv.appendChild(bubble);

    if (sender === 'ai' && source && source !== 'error') {
        const sourceEl = document.createElement('div');
        sourceEl.className = 'message-source';
        const label = source === 'rl_inference' ? '✦ Knowledge-augmented' : '⚡ Direct Ollama';
        sourceEl.textContent = label;
        msgDiv.appendChild(sourceEl);
    }

    messagesArea.appendChild(msgDiv);
    scrollToBottom();
}

function formatMessage(text) {
    // Basic markdown-like formatting
    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic: *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code: `text`
    html = html.replace(/`(.+?)`/g, '<code style="background:rgba(108,99,255,0.15);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}

// ── Typing Indicator ────────────────────────────────────────────

function showTyping() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    msgDiv.id = 'typing-msg';

    const senderLabel = document.createElement('div');
    senderLabel.className = 'message-sender';
    senderLabel.textContent = 'AZAN AI';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;

    msgDiv.appendChild(senderLabel);
    msgDiv.appendChild(bubble);
    messagesArea.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

// ── Helpers ─────────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesArea.scrollTo({
            top: messagesArea.scrollHeight,
            behavior: 'smooth'
        });
    });
}

function autoResize() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
}

// ── Event Listeners ─────────────────────────────────────────────

sendBtn.addEventListener('click', sendMessage);

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

chatInput.addEventListener('input', autoResize);

clearChat.addEventListener('click', () => {
    // Remove all messages, restore welcome screen
    const messages = messagesArea.querySelectorAll('.message');
    messages.forEach(m => m.remove());
    if (welcomeScreen) {
        welcomeScreen.style.display = '';
    }
});

menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !menuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

// Handle paste — clean formatting
chatInput.addEventListener('paste', (e) => {
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    document.execCommand('insertText', false, text);
});