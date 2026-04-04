const API = window.location.origin;
let sess = 'sess_' + Date.now();
let imgs = [], pdfCtx = null, abortCtl = null, isRec = false, recog = null, t0 = 0, toks = 0;

const COMMANDS = [
  { cmd: '@solve', desc: 'Math engine' },
  { cmd: '@factcheck', desc: 'Verification agent' },
  { cmd: '@python:', desc: 'Code runner' },
  { cmd: '@physics', desc: 'Physics solver' },
  { cmd: '@convert', desc: 'Unit conversion' },
  { cmd: '@scrape', desc: 'Web scraper' },
];
let cmdIdx = -1;

function toggleTheme() { const e = document.documentElement, d = e.getAttribute('data-theme') === 'dark'; e.setAttribute('data-theme', d ? 'light' : 'dark'); document.getElementById('themeBtn').textContent = d ? '☀️' : '🌙'; localStorage.setItem('t', d ? 'light' : 'dark'); }
function initTheme() { const t = localStorage.getItem('t') || 'dark'; document.documentElement.setAttribute('data-theme', t); document.getElementById('themeBtn').textContent = t === 'dark' ? '🌙' : '☀️'; }
function toggleSB() { document.getElementById('sidebar').classList.toggle('collapsed'); }

async function loadSessions() {
  try {
    const r = await fetch(API + '/api/sessions'), d = await r.json(), list = document.getElementById('sessList'), ss = d.sessions || [];
    if (!ss.length) { list.innerHTML = '<div style="color:var(--t3);font-size:11px;">No sessions yet</div>'; return; }
    list.innerHTML = ss.map(s => `<div class="sess-item ${s.session_id === sess ? 'active' : ''}" id="si_${s.session_id}" onclick="loadSess('${s.session_id}')"><span class="sess-text">${esc(s.preview || s.session_id || '').substring(0, 38)}</span><span class="sess-del" onclick="delSess('${s.session_id}',event)">✕</span></div>`).join('');
  } catch (e) { }
}
async function newChat() { sess = 'sess_' + Date.now(); document.getElementById('messages').innerHTML = ''; greet(); loadSessions(); }
async function loadSess(id) {
  sess = id; document.querySelectorAll('.sess-item').forEach(e => e.classList.remove('active'));
  const el = document.getElementById('si_' + id); if (el) el.classList.add('active');
  try {
    const r = await fetch(API + '/chat/history/' + id), d = await r.json(), msgs = document.getElementById('messages');
    msgs.innerHTML = ''; (d.messages || []).forEach(m => addMsg(m.content, m.role === 'user' ? 'user' : 'azan', false));
    setTimeout(() => msgs.scrollTop = msgs.scrollHeight, 50);
  } catch (e) { addMsg('Failed to load session.', 'azan'); }
}
async function delSess(id, e) { e.stopPropagation(); try { await fetch(API + '/api/sessions/' + id, { method: 'DELETE' }); } catch (_) { } (id === sess) ? newChat() : loadSessions(); }

async function loadStats() {
  try {
    const [db, tr] = await Promise.all([fetch(API + '/api/db/summary').then(r => r.json()), fetch(API + '/auto-training/stats').then(r => r.json())]);
    document.getElementById('stDB').textContent = db.db_size_kb ? db.db_size_kb + ' KB' : 'OK';
    document.getElementById('stVec').textContent = db.vector_count ?? '–';
    document.getElementById('kbA').textContent = db.articles ?? '0';
    document.getElementById('kbP').textContent = db.training_pairs ?? '0';
    document.getElementById('kbS').textContent = db.sessions ?? '0';
    const tags = db.topics || ['business', 'technology', 'politics', 'world', 'science', 'sports', 'entertainment', 'national'];
    document.getElementById('topicTags').innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('');
    document.getElementById('trSt').textContent = tr.status || '–';
    document.getElementById('trRw').textContent = tr.avg_reward ? parseFloat(tr.avg_reward).toFixed(3) : '–';
    document.getElementById('trSess').textContent = tr.total_sessions ?? '–';
    document.getElementById('trLast').textContent = tr.last_run ? tr.last_run.substring(11, 16) : '–';
  } catch (e) { }
}
async function loadJarvisStatus() {
  try {
    const d = await fetch(API + '/api/jarvis/status').then(r => r.json());
    document.getElementById('jvOrch').textContent = d.orchestrator || '–';
    document.getElementById('jvLearn').textContent = d.continuous_learner || '–';
    const sys = d.system || {};
    document.getElementById('jvCpu').textContent = sys.cpu_percent != null ? sys.cpu_percent.toFixed(1) + '%' : '–';
    const ram = sys.ram || {};
    document.getElementById('jvRam').textContent = ram.percent != null ? ram.percent.toFixed(1) + '%' : '–';
    document.getElementById('jvOllama').textContent = sys.ollama || '–';
    const tasks = (d.scheduled_tasks || []).filter(t => t.status === 'waiting' || t.status === 'running');
    document.getElementById('jvTasks').textContent = tasks.length;
  } catch (e) { }
}
async function loadModels() {
  try {
    const r = await fetch(API + '/api/models'), d = await r.json(), sel = document.getElementById('modelSelect');
    sel.innerHTML = (d.models || ['llama3']).map(m => `<option value="${m}">${m}</option>`).join(''); onMC();
  } catch (e) { }
}
function onMC() { const m = document.getElementById('modelSelect').value;['stModel', 'hdrModel', 'mdlBadge'].forEach(id => document.getElementById(id).textContent = m); }
async function pullModel() {
  const m = document.getElementById('modelSelect').value, st = document.getElementById('pullSt');
  st.textContent = 'Pulling ' + m + '…';
  try { const r = await fetch(API + '/api/models/pull', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: m }) }), d = await r.json(); st.textContent = d.status || 'Done'; }
  catch (e) { st.textContent = 'Failed'; }
}
function loadVoices() { const sel = document.getElementById('voiceSel'), vs = window.speechSynthesis.getVoices(); sel.innerHTML = vs.map((v, i) => `<option value="${i}">${v.name}</option>`).join(''); }
function speakTxt(btn, text) {
  if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); btn.textContent = '🔊'; return; }
  const vs = window.speechSynthesis.getVoices(), idx = parseInt(document.getElementById('voiceSel').value) || 0;
  const u = new SpeechSynthesisUtterance(text); if (vs[idx]) u.voice = vs[idx];
  u.rate = parseFloat(document.getElementById('ttsRate').value) / 100; u.pitch = parseFloat(document.getElementById('ttsPitch').value) / 100;
  u.onend = () => btn.textContent = '🔊'; btn.textContent = '⏹'; window.speechSynthesis.speak(u);
}
function toggleVoice() {
  const btn = document.getElementById('micBtn');
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) { alert('Voice recognition not supported.'); return; }
  if (isRec) { recog.stop(); isRec = false; btn.classList.remove('rec'); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition; recog = new SR(); recog.lang = 'en-US'; recog.interimResults = false;
  recog.onresult = e => { const t = e.results[0][0].transcript, ta = document.getElementById('chatInput'); ta.value = (ta.value + ' ' + t).trim(); autoRz(ta); };
  recog.onend = () => { isRec = false; btn.classList.remove('rec'); };
  recog.start(); isRec = true; btn.classList.add('rec');
}
async function handleFiles(e) { for (const f of e.target.files) (f.type.startsWith('image/')) ? await addImgFile(f) : f.type === 'application/pdf' ? await addPDFFile(f) : null; e.target.value = ''; }
async function addImgFile(file) { return new Promise(res => { const fr = new FileReader(); fr.onload = ev => { const id = 'i' + Date.now(); imgs.push({ id, b64: ev.target.result }); const s = document.getElementById('imgStrip'); s.classList.add('show'); const d = document.createElement('div'); d.className = 'ith'; d.id = id; d.innerHTML = `<img src="${ev.target.result}"><button class="ith-del" onclick="rmImg('${id}')">✕</button>`; s.appendChild(d); res(); }; fr.readAsDataURL(file); }); }
async function addPDFFile(file) { return new Promise(res => { const fr = new FileReader(); fr.onload = ev => { const bytes = new Uint8Array(ev.target.result); let t = ''; for (let i = 0; i < Math.min(bytes.length, 30000); i++)t += String.fromCharCode(bytes[i]); pdfCtx = { name: file.name, text: t.replace(/[^\\x20-\\x7E\\n]/g, ' ').replace(/\\s+/g, ' ').trim().substring(0, 3000) }; addNote('️️ PDF: ' + file.name); res(); }; fr.readAsArrayBuffer(file); }); }
function rmImg(id) { imgs = imgs.filter(x => x.id !== id); const el = document.getElementById(id); if (el) el.remove(); if (!imgs.length) document.getElementById('imgStrip').classList.remove('show'); }
document.addEventListener('dragover', e => { e.preventDefault(); document.getElementById('dropOv').classList.add('on'); });
document.addEventListener('dragleave', e => { if (!e.relatedTarget) document.getElementById('dropOv').classList.remove('on'); });
document.addEventListener('drop', async e => { e.preventDefault(); document.getElementById('dropOv').classList.remove('on'); for (const f of e.dataTransfer.files) (f.type.startsWith('image/')) ? await addImgFile(f) : f.type === 'application/pdf' ? await addPDFFile(f) : null; });
document.addEventListener('paste', async e => { for (const item of e.clipboardData.items) if (item.type.startsWith('image/')) await addImgFile(item.getAsFile()); });
function stopGen() { if (abortCtl) { abortCtl.abort(); abortCtl = null; } document.getElementById('stpBtn').classList.remove('on'); document.getElementById('sndBtn').disabled = false; }

async function sendChat() {
  const ta = document.getElementById('chatInput'); let msg = ta.value.trim();
  if (!msg && !imgs.length) return; if (!msg && imgs.length) msg = 'Describe these images.';
  if (pdfCtx) { msg += '\\n\\n[Context from ' + pdfCtx.name + ']:\\n' + pdfCtx.text; pdfCtx = null; }
  addUserMsg(msg, [...imgs]); ta.value = ''; autoRz(ta);
  const body = { prompt: msg, session_id: sess, model: document.getElementById('modelSelect').value, temperature: parseFloat(document.getElementById('tmpSldr').value) / 100, top_p: parseFloat(document.getElementById('tpSldr').value) / 100, images: imgs.map(i => i.b64.split(',')[1]) };
  imgs = []; const strip = document.getElementById('imgStrip'); strip.innerHTML = ''; strip.classList.remove('show');
  const lc = msg.toLowerCase().trim(); let ac = null, ab = null;
  if (lc.startsWith('fact-check ') || lc.startsWith('factcheck ')) { ac = '/api/agent/fact-check'; ab = { claim: msg.replace(/^fact-?check\\s+/i, '') }; }
  else if (/^(solve|calculate|integrate|differentiate|limit)\\s/.test(lc)) { const t = lc.startsWith('integrate') ? 'integrate' : lc.startsWith('differentiate') ? 'differentiate' : lc.startsWith('limit') ? 'limit' : 'auto'; ac = '/api/agent/execute'; ab = { command: 'solve_math', args: { expression: msg.replace(/^\\w+\\s+/, '').trim(), task: t } }; }
  else if (lc.startsWith('physics ')) { ac = '/api/agent/execute'; ab = { command: 'solve_physics', args: { problem: msg.replace(/^physics\\s+/i, '').trim(), domain: 'auto' } }; }
  else if (lc.startsWith('convert ')) { ac = '/api/agent/execute'; ab = { command: 'unit_convert', args: { problem: msg.replace(/^convert\\s+/i, '').trim() } }; }
  else if (lc.startsWith('python:') || lc.startsWith('code:')) { ac = '/api/agent/execute'; ab = { command: 'run_code', args: { code: msg.replace(/^(python|code):\\s*/i, '').trim(), language: 'python' } }; }
  else if (lc.startsWith('scrape ')) { ac = '/api/agent/execute'; ab = { command: 'scrape', args: { url: msg.replace(/^scrape\\s+/i, '').trim() } }; }
  const sndBtn = document.getElementById('sndBtn'), stpBtn = document.getElementById('stpBtn'), agBar = document.getElementById('agBar');
  sndBtn.disabled = true; const thk = addThinking();
  try {
    if (ac) {
      agBar.classList.add('on'); document.getElementById('agSt').textContent = 'Agent running…';
      const res = await fetch(API + ac, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ab) });
      const data = await res.json(); agBar.classList.remove('on'); thk.remove();
      const content = data.result || data.reasoning || data.detail || JSON.stringify(data, null, 2);
      const badge = ac.includes('fact-check') ? (data.verdict === 'confirmed' ? 'verified' : 'unverified') : null;
      addMsg(content, 'azan', true, badge);
    } else {
      abortCtl = new AbortController(); stpBtn.classList.add('on'); t0 = Date.now(); toks = 0;
      const res = await fetch(API + '/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: abortCtl.signal });
      if (!res.ok) throw new Error('Stream error ' + res.status);
      thk.remove(); const { div: mDiv, bub: bubble } = mkStreamBub();
      const reader = res.body.getReader(), dec = new TextDecoder(); let full = '';
      outer: while (true) {
        const { done, value } = await reader.read(); if (done) break;
        for (const line of dec.decode(value).split('\\n')) {
          if (!line.startsWith('data: ')) continue;
          try { const dd = JSON.parse(line.slice(6)); if (dd.done) break outer; if (dd.token) { full += dd.token; toks++; const tps = (toks / ((Date.now() - t0) / 1000)).toFixed(1); document.getElementById('spdVal').textContent = tps; document.getElementById('spdBadge').classList.add('on'); renderBub(bubble, full, true); scrollBot(); } } catch (_) { }
        }
      }
      renderBub(bubble, full, false); addRxns(mDiv, full); stpBtn.classList.remove('on'); abortCtl = null;
    }
  } catch (e) { if (e.name !== 'AbortError') { try { thk.remove(); } catch (_) { } addMsg('⚠ ' + e.message, 'azan'); } stpBtn.classList.remove('on'); }
  finally { sndBtn.disabled = false; agBar.classList.remove('on'); document.getElementById('chatInput').focus(); loadSessions(); }
}
function addUserMsg(text, images) {
  const msgs = document.getElementById('messages'), div = document.createElement('div'); div.className = 'msg user';
  const imgs2 = images.map(img => `<img class="msg-img" src="${img.b64}" style="max-width:220px;border-radius:8px;display:block;margin-bottom:5px;">`).join('');
  div.innerHTML = `<div class="av u">👤</div><div class="mi"><div class="bub">${imgs2}${esc(text)}</div><div class="mmeta"><span class="mtime">${now()}</span></div></div>`;
  msgs.appendChild(div); scrollBot();
}
function addMsg(text, role, anim = true, badge = null) {
  const msgs = document.getElementById('messages'), div = document.createElement('div'); div.className = 'msg ' + (role === 'user' ? 'user' : 'azan');
  const isAI = role === 'azan';
  const bh = badge ? `<span class="fbadge ${badge}">${badge === 'verified' ? '✓ Verified' : '⚠ Unverified'}</span>` : '';

  // Strip JARVIS ReAct thoughts (Executing Tool... and Observation...) before speaking
  let cleanText = text.replace(/\*\s*\(Executing Tool:.*?\)\s*\*/g, '').replace(/\*\*Observation:\*\*[\s\S]*?```[\s\S]*?```/g, '');
  const cl = cleanText.replace(/[*_#`]/g, '').replace(/"/g, '"').replace(/'/g, "\\'").trim().substring(0, 400);

  const sp = isAI ? `<button class="rb" onclick="speakTxt(this,'${cl}')" title="Speak">🔊</button>` : '';
  const av = isAI ? `<div class="av a">⬡</div>` : `<div class="av u">👤</div>`;
  const content = isAI ? renderMd(text) : esc(text);
  div.innerHTML = `${av}<div class="mi"><div class="bub">${content}</div><div class="mmeta"><span class="mtime">${now()}</span>${bh}<div class="rbtns"><button class="rb" onclick="cpMsg(this,'${cl}')" title="Copy">📋</button>${sp}</div></div></div>`;
  if (isAI && text) renderBub(div.querySelector('.bub'), text, false); msgs.appendChild(div); scrollBot(); return div;
}
function addNote(t) { const msgs = document.getElementById('messages'), d = document.createElement('div'); d.style.cssText = 'text-align:center;font-size:10px;color:var(--t3);padding:5px 0;'; d.textContent = t; msgs.appendChild(d); }
function greet() { addMsg(["Hello! I'm **AZAN**, your intelligent AI assistant.", "", "Powered by Semantic RAG, RL knowledge, and autonomous agents.", "", "Try:", "- `solve x+5=10` — Math engine", "- `fact-check the moon landing` — Verification agent", "- `python: print(42)` — Code runner", "- `physics v=20 u=0 t=5 find a` — Physics solver", "- 📎 Attach an image to analyze it visually"].join("\\n"), 'azan', false); }
function addThinking() { const msgs = document.getElementById('messages'), div = document.createElement('div'); div.className = 'msg azan'; div.innerHTML = `<div class="av a">⬡</div><div class="mi"><div class="thinking"><div class="tdots"><div class="tdot"></div><div class="tdot"></div><div class="tdot"></div></div><span>Thinking…</span></div></div>`; msgs.appendChild(div); scrollBot(); return div; }
function mkStreamBub() { const msgs = document.getElementById('messages'), div = document.createElement('div'); div.className = 'msg azan'; div.innerHTML = `<div class="av a">⬡</div><div class="mi"><div class="bub stream-cursor"></div><div class="mmeta"><span class="mtime">${now()}</span><div class="rbtns"></div></div></div>`; msgs.appendChild(div); scrollBot(); return { div, bub: div.querySelector('.bub') }; }
function addRxns(div, full) {
  let cleanText = full.replace(/\*\s*\(Executing Tool:.*?\)\s*\*/g, '').replace(/\*\*Observation:\*\*[\s\S]*?```[\s\S]*?```/g, '');
  const cl = cleanText.replace(/[*_#`]/g, '').replace(/"/g, '"').replace(/'/g, "\\'").trim().substring(0, 400);
  const rb = div.querySelector('.rbtns'); if (rb) rb.innerHTML = `<button class="rb" onclick="this.classList.toggle('liked')" title="Like">👍</button><button class="rb" onclick="this.classList.toggle('disliked')" title="Dislike">👎</button><button class="rb" onclick="cpMsg(this,'${cl}')" title="Copy">📋</button><button class="rb" onclick="speakTxt(this,'${cl}')" title="Speak">🔊</button>`;
}
function cpMsg(btn, t) { navigator.clipboard.writeText(t).then(() => { btn.textContent = '✓'; setTimeout(() => btn.textContent = '📋', 1500); }); }
function renderMd(t) { if (typeof marked === 'undefined') return esc(t); try { return marked.parse(t); } catch (e) { return esc(t); } }
function renderBub(bub, text, streaming) { if (!bub) return; bub.innerHTML = renderMd(text); bub.classList.toggle('stream-cursor', streaming); if (!streaming) { if (typeof hljs !== 'undefined') bub.querySelectorAll('pre code').forEach(b => { try { hljs.highlightElement(b); } catch (_) { } }); if (typeof renderMathInElement !== 'undefined') renderMathInElement(bub, { delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }, { left: '\\\\\\\\(', right: '\\\\\\\\)', display: false }, { left: '\\\\\\\\[', right: '\\\\\\\\]', display: true }], throwOnError: false }); } }
function onKey(e) {
  const menu = document.getElementById('cmdMenu');
  if (menu && menu.classList.contains('show')) {
    const items = menu.querySelectorAll('.cmd-item');
    if (e.key === 'ArrowDown') { e.preventDefault(); cmdIdx = (cmdIdx + 1) % items.length; updateCmdSel(items); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); cmdIdx = (cmdIdx - 1 + items.length) % items.length; updateCmdSel(items); return; }
    if (e.key === 'Enter') { e.preventDefault(); if (cmdIdx >= 0 && items[cmdIdx]) items[cmdIdx].click(); return; }
    if (e.key === 'Escape') { hideCmdMenu(); return; }
  }
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}
function updateCmdSel(items) { items.forEach((it, i) => it.classList.toggle('active', i === cmdIdx)); if (cmdIdx >= 0) items[cmdIdx].scrollIntoView({ block: 'nearest' }); }
function hideCmdMenu() { const m = document.getElementById('cmdMenu'); if (m) { m.classList.remove('show'); cmdIdx = -1; } }
function pickCmd(cmd) { const ta = document.getElementById('chatInput'); ta.value = ta.value.replace(/(^|\s)@\w*$/, `$1${cmd} `); hideCmdMenu(); ta.focus(); }
function checkCmds(el) {
  autoRz(el);
  const match = el.value.match(/(^|\s)@(\w*)$/);
  const menu = document.getElementById('cmdMenu');
  if (!menu) return;
  if (match) {
    const q = match[2].toLowerCase();
    const hits = COMMANDS.filter(c => c.cmd.toLowerCase().includes(q));
    if (hits.length > 0) {
      menu.innerHTML = hits.map((h, i) => `<div class="cmd-item" onclick="pickCmd('${h.cmd}')"><div class="cmd-lbl">${h.cmd}</div><div class="cmd-desc">${h.desc}</div></div>`).join('');
      menu.classList.add('show'); cmdIdx = -1;
    } else { hideCmdMenu(); }
  } else { hideCmdMenu(); }
}
function autoRz(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 150) + 'px'; }
function scrollBot() { const m = document.getElementById('messages'); if (m) m.scrollTop = m.scrollHeight; }
function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function now() { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
function clearChat() { if (confirm('Clear this chat?')) { document.getElementById('messages').innerHTML = ''; greet(); } }
function initMarked() { if (typeof marked !== 'undefined') try { marked.use({ breaks: true, gfm: true }); } catch (e) { } }
window.speechSynthesis.onvoiceschanged = loadVoices;
window.onload = () => { initTheme(); initMarked(); loadVoices(); loadStats(); loadJarvisStatus(); loadSessions(); loadModels(); greet(); document.getElementById('chatInput').focus(); setInterval(loadStats, 60000); setInterval(loadJarvisStatus, 10000); setInterval(loadSessions, 15000); };