"""
Rebuilds the read_root() HTML template in app.py by replacing
everything between the route decorator and the backend routes.
Run with: python3 rebuild_ui.py
"""
import re

with open('/Applications/AZAN/webui/app.py', 'r') as f:
    content = f.read()

# The new HTML template (complete, phases 5-8)
NEW_TEMPLATE = r'''@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    """AZAN AI Chat — Phases 5-8 Complete Remake."""
    return """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AZAN AI Chat</title>
<meta name="description" content="AZAN — AI powered by Semantic RAG, RL knowledge, and Autonomous Agents.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{
  --bg:#080812;--bg2:#0f0f1e;--bg3:#151528;--bg4:#1a1a32;
  --glass:rgba(255,255,255,0.04);--glass-b:rgba(255,255,255,0.08);
  --accent:#7c5cfc;--accent2:#a78bfa;--glow:rgba(124,92,252,0.3);
  --green:#34d399;--red:#f87171;--orange:#fb923c;
  --t1:#e4e4f0;--t2:#9090b0;--t3:#555570;
  --bdr:rgba(255,255,255,0.07);--r:12px;--rs:8px;
}
[data-theme="light"]{
  --bg:#f0f0f8;--bg2:#fff;--bg3:#e8e8f5;--bg4:#ddddf0;
  --glass:rgba(0,0,0,0.02);--glass-b:rgba(0,0,0,0.08);
  --accent:#6c4ce0;--accent2:#8b6ef0;--glow:rgba(108,76,224,0.2);
  --t1:#1a1a2e;--t2:#555580;--t3:#888899;--bdr:rgba(0,0,0,0.08);
}
html,body{height:100%;background:var(--bg);color:var(--t1);font-family:'Plus Jakarta Sans','Inter',sans-serif;overflow:hidden;}
.layout{display:flex;height:100vh;}
.sidebar{width:290px;min-width:290px;background:var(--bg2);border-right:1px solid var(--bdr);display:flex;flex-direction:column;overflow:hidden;transition:width .3s,min-width .3s;}
.sidebar.collapsed{width:0;min-width:0;}
.main{flex:1;display:flex;flex-direction:column;min-width:0;}
.sb-inner{padding:14px;display:flex;flex-direction:column;gap:10px;height:100%;overflow-y:auto;overflow-x:hidden;}
.sb-inner::-webkit-scrollbar{width:3px;}.sb-inner::-webkit-scrollbar-thumb{background:var(--bdr);}
.logo-row{display:flex;align-items:center;justify-content:space-between;padding-bottom:4px;}
.logo{font-size:19px;font-weight:800;color:var(--accent);letter-spacing:-0.5px;display:flex;align-items:center;gap:8px;}
.logo-v{font-size:10px;background:var(--accent);color:#fff;padding:2px 6px;border-radius:20px;font-weight:600;}
.icon-btn{background:var(--glass);border:1px solid var(--glass-b);color:var(--t2);width:30px;height:30px;border-radius:var(--rs);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all .2s;}
.icon-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent);}
.new-btn{width:100%;padding:9px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border:none;border-radius:var(--rs);font-weight:700;font-size:12px;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;}
.new-btn:hover{transform:translateY(-1px);box-shadow:0 4px 20px var(--glow);}
.card{background:var(--glass);border:1px solid var(--glass-b);border-radius:var(--r);padding:10px;}
.ctitle{font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin-bottom:8px;display:flex;align-items:center;gap:5px;}
.ctitle::before{content:'';width:5px;height:5px;background:var(--accent);border-radius:50%;display:inline-block;}
.sg{display:grid;grid-template-columns:1fr 1fr;gap:5px;}
.si{background:var(--bg3);border-radius:var(--rs);padding:7px 9px;}
.sl{font-size:9px;color:var(--t3);margin-bottom:1px;}
.sv{font-size:12px;font-weight:600;color:var(--t1);}
.sv.ac{color:var(--accent2);}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;animation:pd 2s infinite;margin-right:3px;}
@keyframes pd{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.6;transform:scale(.8);}}
.kbg{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:7px;}
.kbs{text-align:center;background:var(--bg3);border-radius:var(--rs);padding:7px 3px;}
.kbn{font-size:16px;font-weight:800;color:var(--accent2);}
.kbl{font-size:8px;color:var(--t3);text-transform:uppercase;letter-spacing:.5px;}
.tags{display:flex;flex-wrap:wrap;gap:3px;}
.tag{font-size:9px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);padding:2px 7px;border-radius:20px;cursor:pointer;transition:all .2s;}
.tag:hover{background:var(--accent);color:#fff;border-color:var(--accent);}
.msel{width:100%;padding:7px 9px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t1);border-radius:var(--rs);font-size:12px;outline:none;margin-bottom:6px;}
.pbtn{width:100%;padding:6px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);border-radius:var(--rs);font-size:11px;cursor:pointer;transition:all .2s;margin-bottom:6px;}
.pbtn:hover{border-color:var(--accent);color:var(--accent);}
.srow{display:flex;align-items:center;gap:7px;margin-bottom:5px;}
.slbl{font-size:10px;color:var(--t2);width:36px;flex-shrink:0;}
.sldr{flex:1;accent-color:var(--accent);height:3px;}
.sval{font-size:10px;color:var(--accent2);width:28px;text-align:right;}
.sess-list{display:flex;flex-direction:column;gap:3px;max-height:180px;overflow-y:auto;}
.sess-item{padding:7px 9px;background:var(--bg3);border-radius:var(--rs);cursor:pointer;font-size:11px;color:var(--t2);transition:all .2s;display:flex;align-items:center;justify-content:space-between;gap:6px;}
.sess-item:hover,.sess-item.active{background:var(--bg4);color:var(--t1);}
.sess-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;}
.sess-del{opacity:0;font-size:11px;color:var(--red);cursor:pointer;padding:1px 4px;}
.sess-item:hover .sess-del{opacity:1;}
.ch{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--bdr);background:var(--bg2);flex-shrink:0;}
.ch-l{display:flex;align-items:center;gap:10px;}
.tog{background:var(--glass);border:1px solid var(--glass-b);color:var(--t2);width:30px;height:30px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.tog:hover{color:var(--accent);}
.ct{font-size:15px;font-weight:700;color:var(--t1);}
.cs{font-size:11px;color:var(--t3);}
.h-actions{display:flex;gap:6px;align-items:center;}
.mbadge,.spdbadge{background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);padding:4px 10px;border-radius:20px;font-size:11px;}
.spdbadge{color:var(--green);display:none;align-items:center;gap:3px;}
.spdbadge.on{display:flex;}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px;scroll-behavior:smooth;}
.msgs::-webkit-scrollbar{width:3px;}.msgs::-webkit-scrollbar-thumb{background:var(--bdr);}
.msg{display:flex;gap:9px;max-width:800px;animation:mi .25s cubic-bezier(.21,1.02,.73,1) both;}
@keyframes mi{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}
.msg.user{margin-left:auto;flex-direction:row-reverse;}
.msg.azan{margin-right:auto;}
.av{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;}
.av.u{background:linear-gradient(135deg,var(--accent),var(--accent2));}
.av.a{background:var(--bg3);border:1px solid var(--bdr);}
.mi{display:flex;flex-direction:column;gap:3px;max-width:100%;}
.msg.user .mi{align-items:flex-end;}
.bub{background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);padding:11px 15px;font-size:13.5px;line-height:1.7;color:var(--t1);word-break:break-word;}
.msg.user .bub{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-color:transparent;}
.bub .msg-img{max-width:240px;border-radius:8px;margin-top:7px;display:block;}
.mmeta{display:flex;align-items:center;gap:6px;padding:0 2px;}
.mtime{font-size:9px;color:var(--t3);}
.rbtns{display:flex;gap:3px;opacity:0;transition:opacity .2s;}
.msg:hover .rbtns{opacity:1;}
.rb{background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);width:24px;height:24px;border-radius:6px;cursor:pointer;font-size:10px;display:flex;align-items:center;justify-content:center;transition:all .15s;}
.rb:hover{background:var(--bg4);color:var(--accent);border-color:var(--accent);}
.rb.liked{background:var(--green);color:#fff;border-color:var(--green);}
.rb.disliked{background:var(--red);color:#fff;border-color:var(--red);}
.fbadge{font-size:9px;font-weight:600;padding:2px 7px;border-radius:20px;}
.fbadge.verified{background:rgba(52,211,153,.15);color:var(--green);border:1px solid rgba(52,211,153,.3);}
.fbadge.unverified{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3);}
.stream-cursor::after{content:'\\u25ae';animation:blk .7s steps(1) infinite;color:var(--accent);margin-left:2px;}
@keyframes blk{0%,100%{opacity:1;}50%{opacity:0;}}
.thinking{display:flex;align-items:center;gap:8px;padding:10px 15px;background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);font-size:12px;color:var(--t2);}
.tdots{display:flex;gap:3px;}
.tdot{width:5px;height:5px;background:var(--accent);border-radius:50%;animation:tb 1.2s infinite;}
.tdot:nth-child(2){animation-delay:.2s;}.tdot:nth-child(3){animation-delay:.4s;}
@keyframes tb{0%,80%,100%{transform:scale(.6);opacity:.4;}40%{transform:scale(1);opacity:1;}}
.inp-area{padding:14px 20px;border-top:1px solid var(--bdr);background:var(--bg2);}
.inp-box{background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);transition:border-color .2s,box-shadow .2s;}
.inp-box:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--glow);}
.img-strip{display:none;flex-wrap:wrap;gap:5px;padding:9px 11px 0;}
.img-strip.show{display:flex;}
.ith{position:relative;}
.ith img{width:50px;height:50px;object-fit:cover;border-radius:7px;border:1px solid var(--bdr);display:block;}
.ith-del{position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;border:none;border-radius:50%;width:14px;height:14px;font-size:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;}
.inp-row{display:flex;align-items:flex-end;padding:7px 7px 7px 11px;gap:5px;}
.chtxt{flex:1;background:none;border:none;outline:none;color:var(--t1);font-size:13.5px;font-family:inherit;resize:none;min-height:22px;max-height:150px;line-height:1.5;padding-top:3px;}
.chtxt::placeholder{color:var(--t3);}
.iacts{display:flex;gap:3px;align-items:center;flex-shrink:0;}
.abt{background:none;border:none;color:var(--t3);width:32px;height:32px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.abt:hover{color:var(--accent);background:var(--glass);}
.abt.rec{color:var(--red);animation:pr 1s infinite;}
@keyframes pr{0%,100%{opacity:1;}50%{opacity:.4;}}
.snd{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border:none;width:34px;height:34px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.snd:hover{transform:scale(1.05);box-shadow:0 4px 16px var(--glow);}
.snd:disabled{opacity:.4;cursor:not-allowed;transform:none;}
.stpbtn{background:var(--bg3);color:var(--red);border:1px solid var(--bdr);width:34px;height:34px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:none;align-items:center;justify-content:center;}
.stpbtn.on{display:flex;}
.hints{font-size:10px;color:var(--t3);padding:3px 11px 7px;display:flex;gap:5px;flex-wrap:wrap;}
.hints code{background:var(--bg4);color:var(--accent2);padding:1px 5px;border-radius:4px;font-size:9px;cursor:pointer;}
.agbar{display:none;align-items:center;gap:9px;padding:7px 20px;background:rgba(124,92,252,.08);border-top:1px solid rgba(124,92,252,.2);font-size:11px;color:var(--accent2);}
.agbar.on{display:flex;}
.agsp{width:13px;height:13px;border:2px solid rgba(124,92,252,.3);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
.drop-ov{display:none;position:fixed;inset:0;background:rgba(124,92,252,.15);backdrop-filter:blur(4px);z-index:100;align-items:center;justify-content:center;flex-direction:column;gap:10px;border:3px dashed var(--accent);}
.drop-ov.on{display:flex;}
.bub p{margin:5px 0;}.bub p:first-child{margin-top:0;}.bub p:last-child{margin-bottom:0;}
.bub pre{background:#0d1117;border-radius:7px;padding:11px;overflow-x:auto;margin:9px 0;border:1px solid rgba(255,255,255,.08);}
.bub pre code{font-family:'JetBrains Mono','Fira Code',monospace;font-size:12px;color:#e6edf3;}
.bub code:not(pre code){background:rgba(124,92,252,.15);padding:1px 5px;border-radius:4px;font-size:12px;}
.bub h1,.bub h2,.bub h3{color:var(--accent2);margin:10px 0 5px;}
.bub ul,.bub ol{padding-left:18px;margin:7px 0;}
.bub li{margin:3px 0;}
.bub blockquote{border-left:3px solid var(--accent);padding:5px 11px;color:var(--t2);margin:7px 0;}
.bub table{border-collapse:collapse;margin:9px 0;width:100%;}
.bub th,.bub td{border:1px solid var(--bdr);padding:6px 9px;font-size:12px;}
.bub th{background:var(--bg4);}
.bub strong{color:var(--accent2);}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sb-inner">
      <div class="logo-row">
        <div class="logo">&#11041; AZAN <span class="logo-v">v4</span></div>
        <div style="display:flex;gap:5px;">
          <button class="icon-btn" onclick="toggleTheme()" id="themeBtn">&#127769;</button>
        </div>
      </div>
      <button class="new-btn" onclick="newChat()">+ New Chat</button>
      <div class="card">
        <div class="ctitle">System Status</div>
        <div class="sg">
          <div class="si"><div class="sl">Status</div><div class="sv"><span class="dot"></span>Online</div></div>
          <div class="si"><div class="sl">Model</div><div class="sv ac" id="stModel">&#8211;</div></div>
          <div class="si"><div class="sl">Database</div><div class="sv" id="stDB">&#8211;</div></div>
          <div class="si"><div class="sl">Vectors</div><div class="sv" id="stVec">&#8211;</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ctitle">Knowledge Base</div>
        <div class="kbg">
          <div class="kbs"><div class="kbn" id="kbA">0</div><div class="kbl">Articles</div></div>
          <div class="kbs"><div class="kbn" id="kbP">0</div><div class="kbl">Pairs</div></div>
          <div class="kbs"><div class="kbn" id="kbS">0</div><div class="kbl">Sessions</div></div>
        </div>
        <div class="tags" id="topicTags"></div>
      </div>
      <div class="card">
        <div class="ctitle">AI Settings</div>
        <select class="msel" id="modelSelect" onchange="onMC()"><option>llama3</option></select>
        <button class="pbtn" onclick="pullModel()">&#11015; Pull Selected Model</button>
        <div id="pullSt" style="font-size:10px;color:var(--t2);margin-bottom:5px;"></div>
        <div class="srow"><span class="slbl">Temp</span><input type="range" class="sldr" id="tmpSldr" min="0" max="100" value="50" oninput="document.getElementById('tmpV').textContent=(this.value/100).toFixed(2)"><span class="sval" id="tmpV">0.50</span></div>
        <div class="srow"><span class="slbl">Top-P</span><input type="range" class="sldr" id="tpSldr" min="0" max="100" value="90" oninput="document.getElementById('tpV').textContent=(this.value/100).toFixed(2)"><span class="sval" id="tpV">0.90</span></div>
      </div>
      <div class="card">
        <div class="ctitle">Auto-Training</div>
        <div class="sg">
          <div class="si"><div class="sl">Status</div><div class="sv" id="trSt">&#8211;</div></div>
          <div class="si"><div class="sl">Avg Reward</div><div class="sv ac" id="trRw">&#8211;</div></div>
          <div class="si"><div class="sl">Sessions</div><div class="sv" id="trSess">&#8211;</div></div>
          <div class="si"><div class="sl">Last Run</div><div class="sv" id="trLast">&#8211;</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ctitle">Voice Output (TTS)</div>
        <select class="msel" id="voiceSel" style="margin-bottom:5px;"></select>
        <div class="srow"><span class="slbl">Speed</span><input type="range" class="sldr" id="ttsRate" min="50" max="200" value="100" oninput="document.getElementById('rV').textContent=(this.value/100).toFixed(1)+'x'"><span class="sval" id="rV">1.0x</span></div>
        <div class="srow"><span class="slbl">Pitch</span><input type="range" class="sldr" id="ttsPitch" min="50" max="200" value="100" oninput="document.getElementById('pV').textContent=(this.value/100).toFixed(1)"><span class="sval" id="pV">1.0</span></div>
      </div>
      <div class="card" style="flex:1;">
        <div class="ctitle">Chat Sessions</div>
        <div class="sess-list" id="sessList"><div style="color:var(--t3);font-size:11px;">Loading&#8230;</div></div>
      </div>
    </div>
  </aside>
  <div class="main">
    <div class="ch">
      <div class="ch-l">
        <button class="tog" onclick="toggleSB()">&#9776;</button>
        <div>
          <div class="ct">AZAN AI Chat</div>
          <div class="cs">Semantic RAG &#183; RL Knowledge &#183; <span id="hdrModel">Llama3</span></div>
        </div>
      </div>
      <div class="h-actions">
        <div class="spdbadge" id="spdBadge">&#9889; <span id="spdVal">0</span> t/s</div>
        <div class="mbadge" id="mdlBadge">llama3</div>
        <button class="icon-btn" onclick="clearChat()" title="Clear chat">&#128465;</button>
      </div>
    </div>
    <div class="msgs" id="messages"></div>
    <div class="agbar" id="agBar"><div class="agsp"></div><span id="agSt">Running agent&#8230;</span></div>
    <div class="inp-area">
      <div class="inp-box">
        <div class="img-strip" id="imgStrip"></div>
        <div class="inp-row">
          <textarea class="chtxt" id="chatInput" rows="1" placeholder="Ask anything&#8230; or try: solve x+5=10 &#183; fact-check [claim] &#183; python: print(42) &#183; physics v=20 u=0 t=5" onkeydown="onKey(event)" oninput="autoRz(this)"></textarea>
          <div class="iacts">
            <input type="file" id="fileIn" accept="image/*,.pdf" multiple hidden onchange="handleFiles(event)">
            <button class="abt" onclick="document.getElementById('fileIn').click()" title="Attach image or PDF">&#128206;</button>
            <button class="abt" id="micBtn" onclick="toggleVoice()" title="Voice input">&#127897;</button>
            <button class="stpbtn" id="stpBtn" onclick="stopGen()" title="Stop generating">&#9209;</button>
            <button class="snd" id="sndBtn" onclick="sendChat()">&#10148;</button>
          </div>
        </div>
        <div class="hints"><code>solve x²+5x+6</code> <code>integrate sin(x)</code> <code>physics v=20 u=0 t=5</code> <code>fact-check [claim]</code> <code>python: print(42)</code> <code>convert 100 celsius to fahrenheit</code></div>
      </div>
    </div>
  </div>
</div>
<div class="drop-ov" id="dropOv"><div style="font-size:40px;">&#128206;</div><div style="font-size:18px;font-weight:700;color:var(--accent2);">Drop image or PDF to attach</div></div>
<script>
const API = window.location.origin;
let sess = 'sess_' + Date.now();
let imgs = [], pdfCtx = null, abortCtl = null, isRec = false, recog = null, t0 = 0, toks = 0;

function toggleTheme(){const e=document.documentElement,d=e.getAttribute('data-theme')==='dark';e.setAttribute('data-theme',d?'light':'dark');document.getElementById('themeBtn').textContent=d?'\\u2600\\uFE0F':'\\uD83C\\uDF19';localStorage.setItem('t',d?'light':'dark');}
function initTheme(){const t=localStorage.getItem('t')||'dark';document.documentElement.setAttribute('data-theme',t);document.getElementById('themeBtn').textContent=t==='dark'?'\\uD83C\\uDF19':'\\u2600\\uFE0F';}
function toggleSB(){document.getElementById('sidebar').classList.toggle('collapsed');}

async function loadSessions(){
  try{const r=await fetch(API+'/api/sessions'),d=await r.json(),list=document.getElementById('sessList'),ss=d.sessions||[];
  if(!ss.length){list.innerHTML='<div style="color:var(--t3);font-size:11px;">No sessions yet</div>';return;}
  list.innerHTML=ss.map(s=>`<div class="sess-item ${s.session_id===sess?'active':''}" id="si_${s.session_id}" onclick="loadSess('${s.session_id}')"><span class="sess-text">${esc(s.preview||s.session_id||'').substring(0,38)}</span><span class="sess-del" onclick="delSess('${s.session_id}',event)">&#10005;</span></div>`).join('');}catch(e){}
}
async function newChat(){sess='sess_'+Date.now();document.getElementById('messages').innerHTML='';greet();loadSessions();}
async function loadSess(id){
  sess=id;document.querySelectorAll('.sess-item').forEach(e=>e.classList.remove('active'));
  const el=document.getElementById('si_'+id);if(el)el.classList.add('active');
  try{const r=await fetch(API+'/chat/history/'+id),d=await r.json(),msgs=document.getElementById('messages');
  msgs.innerHTML='';(d.messages||[]).forEach(m=>addMsg(m.content,m.role==='user'?'user':'azan',false));
  setTimeout(()=>msgs.scrollTop=msgs.scrollHeight,50);}catch(e){addMsg('Failed to load session.','azan');}
}
async function delSess(id,e){e.stopPropagation();try{await fetch(API+'/api/sessions/'+id,{method:'DELETE'});}catch(_){}(id===sess)?newChat():loadSessions();}

async function loadStats(){
  try{
    const[db,tr]=await Promise.all([fetch(API+'/api/db/summary').then(r=>r.json()),fetch(API+'/auto-training/stats').then(r=>r.json())]);
    document.getElementById('stDB').textContent=db.db_size_kb?db.db_size_kb+' KB':'OK';
    document.getElementById('stVec').textContent=db.vector_count??'\\u2013';
    document.getElementById('kbA').textContent=db.articles??'0';
    document.getElementById('kbP').textContent=db.training_pairs??'0';
    document.getElementById('kbS').textContent=db.sessions??'0';
    const tags=db.topics||['business','technology','politics','world','science','sports','entertainment','national'];
    document.getElementById('topicTags').innerHTML=tags.map(t=>`<span class="tag">${t}</span>`).join('');
    document.getElementById('trSt').textContent=tr.status||'\\u2013';
    document.getElementById('trRw').textContent=tr.avg_reward?parseFloat(tr.avg_reward).toFixed(3):'\\u2013';
    document.getElementById('trSess').textContent=tr.total_sessions??'\\u2013';
    document.getElementById('trLast').textContent=tr.last_run?tr.last_run.substring(11,16):'\\u2013';
  }catch(e){}
}
async function loadModels(){
  try{const r=await fetch(API+'/api/models'),d=await r.json(),sel=document.getElementById('modelSelect');
  sel.innerHTML=(d.models||['llama3']).map(m=>`<option value="${m}">${m}</option>`).join('');onMC();}catch(e){}
}
function onMC(){const m=document.getElementById('modelSelect').value;['stModel','hdrModel','mdlBadge'].forEach(id=>document.getElementById(id).textContent=m);}
async function pullModel(){
  const m=document.getElementById('modelSelect').value,st=document.getElementById('pullSt');
  st.textContent='Pulling '+m+'\\u2026';
  try{const r=await fetch(API+'/api/models/pull',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:m})}),d=await r.json();st.textContent=d.status||'Done';}
  catch(e){st.textContent='Failed';}
}
function loadVoices(){const sel=document.getElementById('voiceSel'),vs=window.speechSynthesis.getVoices();sel.innerHTML=vs.map((v,i)=>`<option value="${i}">${v.name}</option>`).join('');}
function speakTxt(btn,text){
  if(window.speechSynthesis.speaking){window.speechSynthesis.cancel();btn.textContent='\\uD83D\\uDD0A';return;}
  const vs=window.speechSynthesis.getVoices(),idx=parseInt(document.getElementById('voiceSel').value)||0;
  const u=new SpeechSynthesisUtterance(text);if(vs[idx])u.voice=vs[idx];
  u.rate=parseFloat(document.getElementById('ttsRate').value)/100;u.pitch=parseFloat(document.getElementById('ttsPitch').value)/100;
  u.onend=()=>btn.textContent='\\uD83D\\uDD0A';btn.textContent='\\u23F9';window.speechSynthesis.speak(u);
}
function toggleVoice(){
  const btn=document.getElementById('micBtn');
  if(!('webkitSpeechRecognition' in window)&&!('SpeechRecognition' in window)){alert('Voice recognition not supported.');return;}
  if(isRec){recog.stop();isRec=false;btn.classList.remove('rec');return;}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;recog=new SR();recog.lang='en-US';recog.interimResults=false;
  recog.onresult=e=>{const t=e.results[0][0].transcript,ta=document.getElementById('chatInput');ta.value=(ta.value+' '+t).trim();autoRz(ta);};
  recog.onend=()=>{isRec=false;btn.classList.remove('rec');};
  recog.start();isRec=true;btn.classList.add('rec');
}
async function handleFiles(e){for(const f of e.target.files)(f.type.startsWith('image/'))?await addImgFile(f):f.type==='application/pdf'?await addPDFFile(f):null;e.target.value='';}
async function addImgFile(file){return new Promise(res=>{const fr=new FileReader();fr.onload=ev=>{const id='i'+Date.now();imgs.push({id,b64:ev.target.result});const s=document.getElementById('imgStrip');s.classList.add('show');const d=document.createElement('div');d.className='ith';d.id=id;d.innerHTML=`<img src="${ev.target.result}"><button class="ith-del" onclick="rmImg('${id}')">&#10005;</button>`;s.appendChild(d);res();};fr.readAsDataURL(file);});}
async function addPDFFile(file){return new Promise(res=>{const fr=new FileReader();fr.onload=ev=>{const bytes=new Uint8Array(ev.target.result);let t='';for(let i=0;i<Math.min(bytes.length,30000);i++)t+=String.fromCharCode(bytes[i]);pdfCtx={name:file.name,text:t.replace(/[^\\x20-\\x7E\\n]/g,' ').replace(/\\s+/g,' ').trim().substring(0,3000)};addNote('\\uD83D\\uDCC4 PDF: '+file.name);res();};fr.readAsArrayBuffer(file);});}
function rmImg(id){imgs=imgs.filter(x=>x.id!==id);const el=document.getElementById(id);if(el)el.remove();if(!imgs.length)document.getElementById('imgStrip').classList.remove('show');}
document.addEventListener('dragover',e=>{e.preventDefault();document.getElementById('dropOv').classList.add('on');});
document.addEventListener('dragleave',e=>{if(!e.relatedTarget)document.getElementById('dropOv').classList.remove('on');});
document.addEventListener('drop',async e=>{e.preventDefault();document.getElementById('dropOv').classList.remove('on');for(const f of e.dataTransfer.files)(f.type.startsWith('image/'))?await addImgFile(f):f.type==='application/pdf'?await addPDFFile(f):null;});
document.addEventListener('paste',async e=>{for(const item of e.clipboardData.items)if(item.type.startsWith('image/'))await addImgFile(item.getAsFile());});
function stopGen(){if(abortCtl){abortCtl.abort();abortCtl=null;}document.getElementById('stpBtn').classList.remove('on');document.getElementById('sndBtn').disabled=false;}

async function sendChat(){
  const ta=document.getElementById('chatInput');let msg=ta.value.trim();
  if(!msg&&!imgs.length)return;if(!msg&&imgs.length)msg='Describe these images.';
  if(pdfCtx){msg+='\\n\\n[Context from '+pdfCtx.name+']:\\n'+pdfCtx.text;pdfCtx=null;}
  addUserMsg(msg,[...imgs]);ta.value='';autoRz(ta);
  const body={prompt:msg,session_id:sess,model:document.getElementById('modelSelect').value,temperature:parseFloat(document.getElementById('tmpSldr').value)/100,top_p:parseFloat(document.getElementById('tpSldr').value)/100,images:imgs.map(i=>i.b64.split(',')[1])};
  imgs=[];const strip=document.getElementById('imgStrip');strip.innerHTML='';strip.classList.remove('show');
  const lc=msg.toLowerCase().trim();let ac=null,ab=null;
  if(lc.startsWith('fact-check ')||lc.startsWith('factcheck ')){ac='/api/agent/fact-check';ab={claim:msg.replace(/^fact-?check\\s+/i,'')};}
  else if(/^(solve|calculate|integrate|differentiate|limit)\\s/.test(lc)){const t=lc.startsWith('integrate')?'integrate':lc.startsWith('differentiate')?'differentiate':lc.startsWith('limit')?'limit':'auto';ac='/api/agent/execute';ab={command:'solve_math',args:{expression:msg.replace(/^\\w+\\s+/,'').trim(),task:t}};}
  else if(lc.startsWith('physics ')){ac='/api/agent/execute';ab={command:'solve_physics',args:{problem:msg.replace(/^physics\\s+/i,'').trim(),domain:'auto'}};}
  else if(lc.startsWith('convert ')){ac='/api/agent/execute';ab={command:'unit_convert',args:{problem:msg.replace(/^convert\\s+/i,'').trim()}};}
  else if(lc.startsWith('python:')||lc.startsWith('code:')){ac='/api/agent/execute';ab={command:'run_code',args:{code:msg.replace(/^(python|code):\\s*/i,'').trim(),language:'python'}};}
  else if(lc.startsWith('scrape ')){ac='/api/agent/execute';ab={command:'scrape',args:{url:msg.replace(/^scrape\\s+/i,'').trim()}};}
  const sndBtn=document.getElementById('sndBtn'),stpBtn=document.getElementById('stpBtn'),agBar=document.getElementById('agBar');
  sndBtn.disabled=true;const thk=addThinking();
  try{
    if(ac){
      agBar.classList.add('on');document.getElementById('agSt').textContent='Agent running\\u2026';
      const res=await fetch(API+ac,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ab)});
      const data=await res.json();agBar.classList.remove('on');thk.remove();
      const content=data.result||data.reasoning||data.detail||JSON.stringify(data,null,2);
      const badge=ac.includes('fact-check')?(data.verdict==='confirmed'?'verified':'unverified'):null;
      addMsg(content,'azan',true,badge);
    }else{
      abortCtl=new AbortController();stpBtn.classList.add('on');t0=Date.now();toks=0;
      const res=await fetch(API+'/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:abortCtl.signal});
      if(!res.ok)throw new Error('Stream error '+res.status);
      thk.remove();const{div:mDiv,bub:bubble}=mkStreamBub();
      const reader=res.body.getReader(),dec=new TextDecoder();let full='';
      outer:while(true){
        const{done,val}=await reader.read()??{};
        const{done:d2,value}=await reader.read();if(d2)break;
        for(const line of dec.decode(value).split('\\n')){
          if(!line.startsWith('data: '))continue;
          try{const dd=JSON.parse(line.slice(6));if(dd.done)break outer;if(dd.token){full+=dd.token;toks++;const tps=(toks/((Date.now()-t0)/1000)).toFixed(1);document.getElementById('spdVal').textContent=tps;document.getElementById('spdBadge').classList.add('on');renderBub(bubble,full,true);scrollBot();}}catch(_){}
        }
      }
      renderBub(bubble,full,false);addRxns(mDiv,full);stpBtn.classList.remove('on');abortCtl=null;
    }
  }catch(e){if(e.name!=='AbortError'){try{thk.remove();}catch(_){}addMsg('\\u26A0 '+e.message,'azan');}stpBtn.classList.remove('on');}
  finally{sndBtn.disabled=false;agBar.classList.remove('on');document.getElementById('chatInput').focus();loadSessions();}
}
function addUserMsg(text,images){
  const msgs=document.getElementById('messages'),div=document.createElement('div');div.className='msg user';
  const imgs2=images.map(img=>`<img class="msg-img" src="${img.b64}" style="max-width:220px;border-radius:8px;display:block;margin-bottom:5px;">`).join('');
  div.innerHTML=`<div class="av u">\\uD83D\\uDC64</div><div class="mi"><div class="bub">${imgs2}${esc(text)}</div><div class="mmeta"><span class="mtime">${now()}</span></div></div>`;
  msgs.appendChild(div);scrollBot();
}
function addMsg(text,role,anim=true,badge=null){
  const msgs=document.getElementById('messages'),div=document.createElement('div');div.className='msg '+(role==='user'?'user':'azan');
  if(!anim)div.style.animation='none';const isAI=role==='azan';
  const bh=badge?`<span class="fbadge ${badge}">${badge==='verified'?'\\u2713 Verified':'\\u26A0 Unverified'}</span>`:'';
  const cl=text.replace(/[*_#`]/g,'').replace(/"/g,'&quot;').replace(/'/g,"\\'").substring(0,400);
  const sp=isAI?`<button class="rb" onclick="speakTxt(this,'${cl}')" title="Speak">\\uD83D\\uDD0A</button>`:'';
  const av=isAI?`<div class="av a">&#11041;</div>`:`<div class="av u">\\uD83D\\uDC64</div>`;
  const content=isAI?renderMd(text):esc(text);
  div.innerHTML=`${av}<div class="mi"><div class="bub">${content}</div><div class="mmeta"><span class="mtime">${now()}</span>${bh}<div class="rbtns"><button class="rb" onclick="cpMsg(this,'${cl}')" title="Copy">\\uD83D\\uDCCB</button>${sp}</div></div></div>`;
  if(isAI&&text)renderBub(div.querySelector('.bub'),text,false);msgs.appendChild(div);scrollBot();return div;
}
function addNote(t){const msgs=document.getElementById('messages'),d=document.createElement('div');d.style.cssText='text-align:center;font-size:10px;color:var(--t3);padding:5px 0;';d.textContent=t;msgs.appendChild(d);}
function greet(){addMsg('Hello! I\'m **AZAN**, your intelligent AI assistant.\\n\\nI\'m powered by Semantic RAG, RL-enhanced knowledge, and autonomous agents.\\n\\nTry:\\n- `solve x\\u00b2+5x+6` \\u2014 Math engine with LaTeX output\\n- `fact-check the moon landing` \\u2014 Verification agent\\n- `python: print(42)` \\u2014 Code execution\\n- `physics v=20 u=0 t=5 find a` \\u2014 Physics solver\\n- \\uD83D\\uDCCE Attach an image to analyze it visually','azan',false);}
function addThinking(){const msgs=document.getElementById('messages'),div=document.createElement('div');div.className='msg azan';div.innerHTML=`<div class="av a">&#11041;</div><div class="mi"><div class="thinking"><div class="tdots"><div class="tdot"></div><div class="tdot"></div><div class="tdot"></div></div><span>Thinking&#8230;</span></div></div>`;msgs.appendChild(div);scrollBot();return div;}
function mkStreamBub(){const msgs=document.getElementById('messages'),div=document.createElement('div');div.className='msg azan';div.innerHTML=`<div class="av a">&#11041;</div><div class="mi"><div class="bub stream-cursor"></div><div class="mmeta"><span class="mtime">${now()}</span><div class="rbtns"></div></div></div>`;msgs.appendChild(div);scrollBot();return{div,bub:div.querySelector('.bub')};}
function addRxns(div,full){const cl=full.replace(/[*_#`]/g,'').replace(/"/g,'&quot;').replace(/'/g,"\\'").substring(0,400);const rb=div.querySelector('.rbtns');if(rb)rb.innerHTML=`<button class="rb" onclick="this.classList.toggle('liked')" title="Like">\\uD83D\\uDC4D</button><button class="rb" onclick="this.classList.toggle('disliked')" title="Dislike">\\uD83D\\uDC4E</button><button class="rb" onclick="cpMsg(this,'${cl}')" title="Copy">\\uD83D\\uDCCB</button><button class="rb" onclick="speakTxt(this,'${cl}')" title="Speak">\\uD83D\\uDD0A</button>`;}
function cpMsg(btn,t){navigator.clipboard.writeText(t).then(()=>{btn.textContent='\\u2713';setTimeout(()=>btn.textContent='\\uD83D\\uDCCB',1500);});}
function renderMd(t){if(typeof marked==='undefined')return esc(t);try{return marked.parse(t);}catch(e){return esc(t);}}
function renderBub(bub,text,streaming){if(!bub)return;bub.innerHTML=renderMd(text);bub.classList.toggle('stream-cursor',streaming);if(!streaming){if(typeof hljs!=='undefined')bub.querySelectorAll('pre code').forEach(b=>{try{hljs.highlightElement(b);}catch(_){}});if(typeof renderMathInElement!=='undefined')renderMathInElement(bub,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\\\\\\\(',right:'\\\\\\\\)',display:false},{left:'\\\\\\\\[',right:'\\\\\\\\]',display:true}],throwOnError:false});}}
function onKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChat();}}
function autoRz(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,150)+'px';}
function scrollBot(){const m=document.getElementById('messages');if(m)m.scrollTop=m.scrollHeight;}
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function now(){return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}
function clearChat(){if(confirm('Clear this chat?')){document.getElementById('messages').innerHTML='';greet();}}
function initMarked(){if(typeof marked!=='undefined')try{marked.use({breaks:true,gfm:true});}catch(e){}}
window.speechSynthesis.onvoiceschanged=loadVoices;
window.onload=()=>{initTheme();initMarked();loadVoices();loadStats();loadSessions();loadModels();greet();document.getElementById('chatInput').focus();setInterval(loadStats,60000);setInterval(loadSessions,15000);};
</script>
</body>
</html>"""
'''

# Replace read_root() function in app.py
# Find its bounds
start_marker = "@app.get(\"/\", response_class=HTMLResponse)"
end_marker = "\n# ============================================================================\n# ROUTE 2: CHAT API (/chat)"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Could not find markers in app.py")
    print("start:", start_idx, "end:", end_idx)
    exit(1)

new_content = content[:start_idx] + NEW_TEMPLATE + "\n" + content[end_idx:]

with open('/Applications/AZAN/webui/app.py', 'w') as f:
    f.write(new_content)

print("app.py updated successfully. New size:", len(new_content))
