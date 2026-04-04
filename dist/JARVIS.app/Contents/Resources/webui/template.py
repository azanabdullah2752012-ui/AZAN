
JS = r"""
const API = window.location.origin;
let currentSession = 'sess_' + Date.now();
let selectedImages = [];
let selectedPDF = null;
let abortController = null;
let recognizing = false;
let recognition = null;
let streamStart = 0, tokenCount = 0;

function toggleTheme() {
    const el = document.documentElement;
    const isDark = el.getAttribute('data-theme') === 'dark';
    el.setAttribute('data-theme', isDark ? 'light' : 'dark');
    document.getElementById('themeBtn').textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
}
function initTheme() {
    const t = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', t);
    document.getElementById('themeBtn').textContent = t === 'dark' ? '🌙' : '☀️';
}
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('collapsed'); }

async function loadSessions() {
    try {
        const r = await fetch(API + '/api/sessions');
        const d = await r.json();
        const list = document.getElementById('sessionList');
        const sessions = d.sessions || [];
        if (!sessions.length) { list.innerHTML = '<div style="color:var(--text3);font-size:12px;">No sessions yet</div>'; return; }
        list.innerHTML = sessions.map(s => {
            const preview = (s.preview || s.session_id || '').substring(0, 40);
            return `<div class="session-item ${s.session_id === currentSession ? 'active' : ''}" id="si_${s.session_id}" onclick="loadSession('${s.session_id}')"><span class="session-text">${escHtml(preview) || s.session_id.substring(5,15)}</span><span class="del" onclick="delSession('${s.session_id}',event)">✕</span></div>`;
        }).join('');
    } catch(e) {}
}
async function newChat() {
    currentSession = 'sess_' + Date.now();
    document.getElementById('messages').innerHTML = '';
    addGreeting();
    loadSessions();
}
async function loadSession(id) {
    currentSession = id;
    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
    const el = document.getElementById('si_' + id);
    if (el) el.classList.add('active');
    try {
        const r = await fetch(API + '/chat/history/' + id);
        const d = await r.json();
        const msgs = document.getElementById('messages');
        msgs.innerHTML = '';
        (d.messages || []).forEach(m => addMessage(m.content, m.role === 'user' ? 'user' : 'azan', false));
        setTimeout(() => msgs.scrollTop = msgs.scrollHeight, 50);
    } catch(e) { addMessage('Failed to load session.', 'azan'); }
}
async function delSession(id, e) {
    e.stopPropagation();
    try { await fetch(API + '/api/sessions/' + id, { method: 'DELETE' }); } catch(_) {}
    if (id === currentSession) newChat(); else loadSessions();
}

async function loadStats() {
    try {
        const [db, tr] = await Promise.all([
            fetch(API + '/api/db/summary').then(r => r.json()),
            fetch(API + '/auto-training/stats').then(r => r.json())
        ]);
        document.getElementById('statusDB').textContent = db.db_size_kb ? db.db_size_kb + ' KB' : 'OK';
        document.getElementById('statusVectors').textContent = db.vector_count ?? '–';
        document.getElementById('kbArticles').textContent = db.articles ?? '0';
        document.getElementById('kbPairs').textContent = db.training_pairs ?? '0';
        document.getElementById('kbSessions').textContent = db.sessions ?? '0';
        const tags = db.topics || ['business','technology','politics','world','science','sports','entertainment','national'];
        document.getElementById('topicTags').innerHTML = tags.map(t => `<span class="topic-tag">${t}</span>`).join('');
        document.getElementById('trainStatus').textContent = tr.status || '–';
        document.getElementById('trainReward').textContent = tr.avg_reward ? parseFloat(tr.avg_reward).toFixed(3) : '–';
        document.getElementById('trainSessions').textContent = tr.total_sessions ?? '–';
        document.getElementById('trainLast').textContent = tr.last_run ? tr.last_run.substring(11,16) : '–';
    } catch(e) {}
}
async function loadModels() {
    try {
        const r = await fetch(API + '/api/models');
        const d = await r.json();
        const sel = document.getElementById('modelSelect');
        sel.innerHTML = (d.models || ['llama3']).map(m => `<option value="${m}">${m}</option>`).join('');
        onModelChange();
    } catch(e) {}
}
function onModelChange() {
    const m = document.getElementById('modelSelect').value;
    document.getElementById('statusModel').textContent = m;
    document.getElementById('headerModel').textContent = m;
    document.getElementById('modelBadge').textContent = m;
}
async function pullModel() {
    const m = document.getElementById('modelSelect').value;
    const st = document.getElementById('pullStatus');
    st.textContent = 'Pulling ' + m + '…';
    try {
        const r = await fetch(API + '/api/models/pull', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({model:m})});
        const d = await r.json();
        st.textContent = d.status || 'Done';
    } catch(e) { st.textContent = 'Failed'; }
}

function loadVoices() {
    const sel = document.getElementById('voiceSelect');
    const voices = window.speechSynthesis.getVoices();
    sel.innerHTML = voices.map((v,i) => `<option value="${i}">${v.name}</option>`).join('');
}
function speakText(btn, text) {
    if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); btn.textContent = '🔊'; return; }
    const voices = window.speechSynthesis.getVoices();
    const idx = parseInt(document.getElementById('voiceSelect').value) || 0;
    const utt = new SpeechSynthesisUtterance(text);
    if (voices[idx]) utt.voice = voices[idx];
    utt.rate = parseFloat(document.getElementById('ttsRate').value) / 100;
    utt.pitch = parseFloat(document.getElementById('ttsPitch').value) / 100;
    utt.onend = () => btn.textContent = '🔊';
    btn.textContent = '⏹';
    window.speechSynthesis.speak(utt);
}
function toggleVoice() {
    const btn = document.getElementById('micBtn');
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) { alert('Voice not supported.'); return; }
    if (recognizing) { recognition.stop(); recognizing = false; btn.classList.remove('recording'); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR(); recognition.lang = 'en-US'; recognition.interimResults = false;
    recognition.onresult = e => { const t = e.results[0][0].transcript; const ta = document.getElementById('chatInput'); ta.value = (ta.value + ' ' + t).trim(); autoResize(ta); };
    recognition.onend = () => { recognizing = false; btn.classList.remove('recording'); };
    recognition.start(); recognizing = true; btn.classList.add('recording');
}

async function handleFiles(e) {
    for (const file of e.target.files) {
        if (file.type.startsWith('image/')) await addImageFile(file);
        else if (file.type === 'application/pdf') await addPDFFile(file);
    }
    e.target.value = '';
}
async function addImageFile(file) {
    return new Promise(res => {
        const fr = new FileReader();
        fr.onload = ev => {
            const id = 'img_' + Date.now();
            selectedImages.push({ id, base64: ev.target.result });
            const strip = document.getElementById('imgStrip');
            strip.classList.add('show');
            const thumb = document.createElement('div');
            thumb.className = 'img-thumb'; thumb.id = id;
            thumb.innerHTML = `<img src="${ev.target.result}"><button class="img-thumb-del" onclick="removeImg('${id}')">✕</button>`;
            strip.appendChild(thumb); res();
        };
        fr.readAsDataURL(file);
    });
}
async function addPDFFile(file) {
    return new Promise(res => {
        const fr = new FileReader();
        fr.onload = ev => {
            const bytes = new Uint8Array(ev.target.result);
            let text = '';
            for (let i = 0; i < Math.min(bytes.length, 30000); i++) text += String.fromCharCode(bytes[i]);
            const clean = text.replace(/[^\x20-\x7E\n]/g,' ').replace(/\s+/g,' ').trim().substring(0,3000);
            selectedPDF = { name: file.name, text: clean };
            addSystemNote('📄 PDF attached: ' + file.name); res();
        };
        fr.readAsArrayBuffer(file);
    });
}
function removeImg(id) {
    selectedImages = selectedImages.filter(x => x.id !== id);
    const el = document.getElementById(id); if (el) el.remove();
    if (!selectedImages.length) document.getElementById('imgStrip').classList.remove('show');
}

document.addEventListener('dragover', e => { e.preventDefault(); document.getElementById('dropOverlay').classList.add('show'); });
document.addEventListener('dragleave', e => { if (!e.relatedTarget) document.getElementById('dropOverlay').classList.remove('show'); });
document.addEventListener('drop', async e => {
    e.preventDefault(); document.getElementById('dropOverlay').classList.remove('show');
    for (const file of e.dataTransfer.files) {
        if (file.type.startsWith('image/')) await addImageFile(file);
        else if (file.type === 'application/pdf') await addPDFFile(file);
    }
});
document.addEventListener('paste', async e => {
    for (const item of e.clipboardData.items)
        if (item.type.startsWith('image/')) await addImageFile(item.getAsFile());
});

function stopGeneration() {
    if (abortController) { abortController.abort(); abortController = null; }
    document.getElementById('stopBtn').classList.remove('show');
    document.getElementById('sendBtn').disabled = false;
}

async function sendChat() {
    const ta = document.getElementById('chatInput');
    let msg = ta.value.trim();
    if (!msg && !selectedImages.length) return;
    if (!msg && selectedImages.length) msg = 'Describe these images.';
    if (selectedPDF) { msg += '\n\n[Context from ' + selectedPDF.name + ']:\n' + selectedPDF.text; selectedPDF = null; }

    addUserMessage(msg, [...selectedImages]);
    ta.value = ''; autoResize(ta);

    const body = {
        prompt: msg, session_id: currentSession,
        model: document.getElementById('modelSelect').value,
        temperature: parseFloat(document.getElementById('tempSlider').value) / 100,
        top_p: parseFloat(document.getElementById('topPSlider').value) / 100,
        images: selectedImages.map(img => img.base64.split(',')[1])
    };
    selectedImages = [];
    const strip = document.getElementById('imgStrip');
    strip.innerHTML = ''; strip.classList.remove('show');

    const lc = msg.toLowerCase().trim();
    let agentCmd = null, agentBody = null;
    if (lc.startsWith('fact-check ') || lc.startsWith('factcheck ')) { agentCmd='/api/agent/fact-check'; agentBody={claim:msg.replace(/^fact-?check\s+/i,'')}; }
    else if (lc.startsWith('solve ') || lc.startsWith('calculate ') || lc.startsWith('integrate ') || lc.startsWith('differentiate ') || lc.startsWith('limit ')) {
        const t = lc.startsWith('integrate') ? 'integrate' : lc.startsWith('differentiate') ? 'differentiate' : lc.startsWith('limit') ? 'limit' : 'auto';
        agentCmd='/api/agent/execute'; agentBody={command:'solve_math',args:{expression:msg.replace(/^\w+\s+/,'').trim(),task:t}};
    } else if (lc.startsWith('physics ')) { agentCmd='/api/agent/execute'; agentBody={command:'solve_physics',args:{problem:msg.replace(/^physics\s+/i,'').trim(),domain:'auto'}}; }
    else if (lc.startsWith('convert ')) { agentCmd='/api/agent/execute'; agentBody={command:'unit_convert',args:{problem:msg.replace(/^convert\s+/i,'').trim()}}; }
    else if (lc.startsWith('python:') || lc.startsWith('code:')) { agentCmd='/api/agent/execute'; agentBody={command:'run_code',args:{code:msg.replace(/^(python|code):\s*/i,'').trim(),language:'python'}}; }
    else if (lc.startsWith('scrape ')) { agentCmd='/api/agent/execute'; agentBody={command:'scrape',args:{url:msg.replace(/^scrape\s+/i,'').trim()}}; }

    const sendBtn=document.getElementById('sendBtn'), stopBtn=document.getElementById('stopBtn'), agentBar=document.getElementById('agentBar');
    sendBtn.disabled = true;
    const thinkEl = addThinking();

    try {
        if (agentCmd) {
            agentBar.classList.add('show');
            document.getElementById('agentStatus').textContent = 'Agent running…';
            const res = await fetch(API + agentCmd, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(agentBody)});
            const data = await res.json();
            agentBar.classList.remove('show'); thinkEl.remove();
            const content = data.result || data.reasoning || data.detail || JSON.stringify(data,null,2);
            const badge = agentCmd.includes('fact-check') ? (data.verdict==='confirmed'?'verified':'unverified') : null;
            addMessage(content, 'azan', true, badge);
        } else {
            abortController = new AbortController(); stopBtn.classList.add('show');
            streamStart = Date.now(); tokenCount = 0;
            const res = await fetch(API+'/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:abortController.signal});
            if (!res.ok) throw new Error('Stream error ' + res.status);
            thinkEl.remove();
            const {div:mDiv, bubble} = createStreamBubble();
            const reader = res.body.getReader(); const dec = new TextDecoder(); let fullText = '';
            outer: while (true) {
                const {done,value} = await reader.read(); if (done) break;
                for (const line of dec.decode(value).split('\n')) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const d = JSON.parse(line.slice(6));
                        if (d.done) break outer;
                        if (d.token) {
                            fullText += d.token; tokenCount++;
                            const tps = (tokenCount / ((Date.now()-streamStart)/1000)).toFixed(1);
                            document.getElementById('speedVal').textContent = tps;
                            document.getElementById('speedBadge').classList.add('visible');
                            renderBubble(bubble, fullText, true); scrollBottom();
                        }
                    } catch(_) {}
                }
            }
            renderBubble(bubble, fullText, false); addReactions(mDiv, fullText);
            stopBtn.classList.remove('show'); abortController = null;
        }
    } catch(e) {
        if (e.name !== 'AbortError') { try{ thinkEl.remove(); }catch(_){} addMessage('⚠ ' + e.message, 'azan'); }
        stopBtn.classList.remove('show');
    } finally {
        sendBtn.disabled = false; agentBar.classList.remove('show');
        document.getElementById('chatInput').focus(); loadSessions();
    }
}

function addUserMessage(text, images) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div'); div.className = 'msg user';
    const imgHtml = images.map(img => `<img class="msg-img" src="${img.base64}" style="max-width:200px;border-radius:8px;display:block;margin-bottom:6px;">`).join('');
    div.innerHTML = `<div class="avatar user-av">👤</div><div class="msg-inner"><div class="bubble">${imgHtml}${escHtml(text)}</div><div class="msg-meta"><span class="msg-time">${now()}</span></div></div>`;
    msgs.appendChild(div); scrollBottom();
}
function addMessage(text, role, animate=true, badge=null) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div'); div.className = 'msg ' + (role==='user'?'user':'azan');
    if (!animate) div.style.animation = 'none';
    const isAI = role === 'azan';
    const badgeHtml = badge ? `<span class="fact-badge ${badge}">${badge==='verified'?'✓ Verified':'⚠ Unverified'}</span>` : '';
    const clean = text.replace(/[*_#`]/g,'').replace(/"/g,'&quot;').replace(/'/g,"\\'").substring(0,400);
    const sp = isAI ? `<button class="react-btn" onclick="speakText(this,'${clean}')" title="Speak">🔊</button>` : '';
    const av = isAI ? `<div class="avatar ai-av">⬡</div>` : `<div class="avatar user-av">👤</div>`;
    const content = isAI ? renderMd(text) : escHtml(text);
    div.innerHTML = `${av}<div class="msg-inner"><div class="bubble">${content}</div><div class="msg-meta"><span class="msg-time">${now()}</span>${badgeHtml}<div class="react-btns"><button class="react-btn" onclick="copyMsg(this,'${clean}')" title="Copy">📋</button>${sp}</div></div></div>`;
    if (isAI && text) renderBubble(div.querySelector('.bubble'), text, false);
    msgs.appendChild(div); scrollBottom(); return div;
}
function addSystemNote(text) {
    const msgs = document.getElementById('messages'); const div=document.createElement('div');
    div.style.cssText='text-align:center;font-size:11px;color:var(--text3);padding:6px 0;';
    div.textContent=text; msgs.appendChild(div);
}
function addGreeting() {
    addMessage('Hello! I\'m **AZAN**, your intelligent AI assistant.\\n\\nI\'m powered by Semantic RAG, RL-enhanced knowledge, and autonomous agents. Try:\\n- `solve x²+5x+6` — math engine\\n- `fact-check the moon landing` — verification agent\\n- `python: print(42)` — code execution\\n- 📎 Attach an image to analyze it visually', 'azan', false);
}
function addThinking() {
    const msgs = document.getElementById('messages'); const div=document.createElement('div');
    div.className = 'msg azan';
    div.innerHTML = `<div class="avatar ai-av">⬡</div><div class="msg-inner"><div class="thinking"><div class="t-dots"><div class="t-dot"></div><div class="t-dot"></div><div class="t-dot"></div></div><span>Thinking…</span></div></div>`;
    msgs.appendChild(div); scrollBottom(); return div;
}
function createStreamBubble() {
    const msgs = document.getElementById('messages'); const div=document.createElement('div');
    div.className = 'msg azan';
    div.innerHTML = `<div class="avatar ai-av">⬡</div><div class="msg-inner"><div class="bubble stream-cursor"></div><div class="msg-meta"><span class="msg-time">${now()}</span><div class="react-btns"></div></div></div>`;
    msgs.appendChild(div); scrollBottom(); return {div, bubble: div.querySelector('.bubble')};
}
function addReactions(div, fullText) {
    const clean = fullText.replace(/[*_#`]/g,'').replace(/"/g,'&quot;').replace(/'/g,"\\'").substring(0,400);
    const rb = div.querySelector('.react-btns');
    if (rb) rb.innerHTML = `<button class="react-btn" onclick="this.classList.toggle('liked')" title="Like">👍</button><button class="react-btn" onclick="this.classList.toggle('disliked')" title="Dislike">👎</button><button class="react-btn" onclick="copyMsg(this,'${clean}')" title="Copy">📋</button><button class="react-btn" onclick="speakText(this,'${clean}')" title="Speak">🔊</button>`;
}
function copyMsg(btn, text) { navigator.clipboard.writeText(text).then(() => { btn.textContent='✓'; setTimeout(()=>btn.textContent='📋',1500); }); }
function renderMd(text) { if (typeof marked==='undefined') return escHtml(text); try { return marked.parse(text); } catch(e) { return escHtml(text); } }
function renderBubble(bubble, text, streaming) {
    if (!bubble) return;
    bubble.innerHTML = renderMd(text);
    bubble.classList.toggle('stream-cursor', streaming);
    if (!streaming) {
        if (typeof hljs!=='undefined') bubble.querySelectorAll('pre code').forEach(b => { try { hljs.highlightElement(b); } catch(_){} });
        if (typeof renderMathInElement!=='undefined') renderMathInElement(bubble, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false},{left:'\\\\[',right:'\\\\]',display:true}],throwOnError:false});
    }
}
function onKey(e) { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } }
function autoResize(el) { el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,160)+'px'; }
function scrollBottom() { const m=document.getElementById('messages'); if(m) m.scrollTop=m.scrollHeight; }
function escHtml(t) { const d=document.createElement('div'); d.textContent=t; return d.innerHTML; }
function now() { return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}); }
function clearChat() { if(confirm('Clear chat?')){ document.getElementById('messages').innerHTML=''; addGreeting(); } }
function initMarked() { if (typeof marked!=='undefined') try { marked.use({breaks:true,gfm:true}); } catch(e) {} }
window.speechSynthesis.onvoiceschanged = loadVoices;
window.onload = () => {
    initTheme(); initMarked(); loadVoices(); loadStats(); loadSessions(); loadModels(); addGreeting();
    document.getElementById('chatInput').focus();
    setInterval(loadStats, 60000); setInterval(loadSessions, 15000);
};
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AZAN AI Chat</title>
<meta name="description" content="AZAN — AI assistant powered by RL knowledge, semantic RAG, and autonomous agents.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>""" + CSS + """</style>
</head>
<body>
""" + BODY_HTML + """
<script>
""" + JS + """
</script>
</body>
</html>"""
