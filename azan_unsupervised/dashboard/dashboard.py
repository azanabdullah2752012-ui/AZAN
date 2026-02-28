"""
dashboard.py — Real-time monitoring dashboard HTML (self-contained).

Returns pure HTML with embedded Chart.js + JS polling.
Served by FastAPI at /dashboard.
No external server needed — just FastAPI.
"""


def get_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AZAN — Knowledge System Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --accent: #58a6ff;
      --green: #3fb950;
      --yellow: #d29922;
      --red: #f85149;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --radius: 10px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'SF Mono', 'Fira Code', monospace;
      padding: 24px;
      min-height: 100vh;
    }
    header {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 28px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
    }
    header h1 {
      font-size: 1.4rem;
      color: var(--accent);
      letter-spacing: 2px;
      text-transform: uppercase;
    }
    .badge {
      background: var(--green);
      color: #000;
      font-size: 0.65rem;
      padding: 2px 8px;
      border-radius: 20px;
      font-weight: bold;
      letter-spacing: 1px;
    }
    .badge.red { background: var(--red); color: #fff; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
    }
    .card .label {
      font-size: 0.7rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 8px;
    }
    .card .value {
      font-size: 1.9rem;
      font-weight: bold;
      color: var(--accent);
    }
    .card .sub { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 24px;
    }
    @media (max-width: 768px) { .row { grid-template-columns: 1fr; } }
    .chart-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
    }
    .chart-card h3 {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 14px;
    }
    .log-box {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      height: 200px;
      overflow-y: auto;
      font-size: 0.72rem;
      color: var(--green);
      line-height: 1.7;
    }
    .log-box .log-err { color: var(--red); }
    .log-box .log-info { color: var(--text-muted); }
    .refresh-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--green);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    .chat-area {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
      margin-bottom: 24px;
    }
    .chat-area h3 {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 14px;
    }
    .chat-input-row {
      display: flex;
      gap: 10px;
    }
    .chat-input-row input {
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px 14px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.85rem;
      outline: none;
    }
    .chat-input-row input:focus { border-color: var(--accent); }
    .chat-input-row button {
      background: var(--accent);
      color: #000;
      border: none;
      border-radius: 6px;
      padding: 10px 20px;
      font-family: inherit;
      font-weight: bold;
      cursor: pointer;
      font-size: 0.85rem;
    }
    .chat-input-row button:hover { opacity: 0.85; }
    .chat-result {
      margin-top: 14px;
      font-size: 0.82rem;
      line-height: 1.7;
      color: var(--text);
      background: var(--bg);
      border-radius: 6px;
      padding: 12px 16px;
      display: none;
      white-space: pre-wrap;
    }
    .source-tag {
      display: inline-block;
      background: #1f2937;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 0.68rem;
      color: var(--yellow);
      margin: 2px 3px 2px 0;
    }
  </style>
</head>
<body>

<header>
  <h1>⚡ AZAN</h1>
  <span style="color:var(--text-muted);font-size:0.8rem;">Unsupervised Knowledge System</span>
  <span class="badge" id="status-badge">LOADING</span>
</header>

<div class="refresh-bar">
  <div class="dot" id="pulse-dot"></div>
  <span id="last-updated">Connecting...</span>
</div>

<!-- Stat cards -->
<div class="grid">
  <div class="card">
    <div class="label">Knowledge Entries</div>
    <div class="value" id="stat-entries">—</div>
    <div class="sub">indexed in FAISS</div>
  </div>
  <div class="card">
    <div class="label">Embedding Cache</div>
    <div class="value" id="stat-cache">—</div>
    <div class="sub">cached vectors</div>
  </div>
  <div class="card">
    <div class="label">Clusters</div>
    <div class="value" id="stat-clusters">—</div>
    <div class="sub">semantic groups</div>
  </div>
  <div class="card">
    <div class="label">Index Size</div>
    <div class="value" id="stat-index">—</div>
    <div class="sub">in memory</div>
  </div>
  <div class="card">
    <div class="label">RAM Usage</div>
    <div class="value" id="stat-ram">—</div>
    <div class="sub">process memory</div>
  </div>
  <div class="card">
    <div class="label">Uptime</div>
    <div class="value" id="stat-uptime">—</div>
    <div class="sub">since start</div>
  </div>
</div>

<div class="row">
  <!-- Cluster Chart -->
  <div class="chart-card">
    <h3>Cluster Distribution</h3>
    <canvas id="clusterChart" height="160"></canvas>
  </div>

  <!-- Background Loop Log -->
  <div class="chart-card">
    <h3>Background Indexer Status</h3>
    <div class="log-box" id="log-box">
      <div class="log-info">Waiting for system data...</div>
    </div>
  </div>
</div>

<!-- Quick Search / Chat -->
<div class="chat-area">
  <h3>🔍 Quick Knowledge Search</h3>
  <div class="chat-input-row">
    <input type="text" id="search-input" placeholder="Ask a question or search knowledge base..." />
    <button onclick="doSearch()">Search</button>
    <button onclick="doChat()" style="background:var(--green)">Chat</button>
  </div>
  <div class="chat-result" id="chat-result"></div>
</div>

<script>
let clusterChart = null;

async function fetchMetrics() {
  try {
    const [metricsRes, statusRes] = await Promise.all([
      fetch('/system/metrics'),
      fetch('/system/status')
    ]);
    const metrics = await metricsRes.json();
    const status = await statusRes.json();

    document.getElementById('stat-entries').textContent = metrics.embedding_count ?? '—';
    document.getElementById('stat-cache').textContent = metrics.cache_size ?? '—';
    document.getElementById('stat-clusters').textContent = metrics.cluster_count ?? '—';
    document.getElementById('stat-index').textContent = (metrics.index_size_mb ?? 0) + ' MB';
    document.getElementById('stat-ram').textContent = (metrics.memory_used_mb ?? 0) + ' MB';
    document.getElementById('stat-uptime').textContent = formatUptime(metrics.uptime_seconds ?? 0);

    const badge = document.getElementById('status-badge');
    if (status.running) {
      badge.textContent = 'RUNNING';
      badge.className = 'badge';
    } else {
      badge.textContent = 'STOPPED';
      badge.className = 'badge red';
    }

    // Log box
    const lernerStatus = metrics.learner_status || {};
    const logBox = document.getElementById('log-box');
    const loop = lernerStatus.loop_iteration ?? 0;
    const newSince = lernerStatus.new_since_start ?? 0;
    const lastIdx = lernerStatus.last_index_time ? new Date(lernerStatus.last_index_time * 1000).toLocaleTimeString() : 'N/A';
    logBox.innerHTML = `
      <div>🔄 Loop iterations: <b>${loop}</b></div>
      <div>📥 New entries since start: <b>${newSince}</b></div>
      <div>⏱ Last index time: <b>${lastIdx}</b></div>
      <div>📚 Total indexed: <b>${lernerStatus.total_indexed ?? metrics.embedding_count ?? 0}</b></div>
      ${lernerStatus.error ? '<div class="log-err">⚠ Error: ' + lernerStatus.error + '</div>' : ''}
      <div class="log-info">Poll interval: every 5s | Watching knowledge_base.txt</div>
    `;

    document.getElementById('last-updated').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById('last-updated').textContent = 'Error: ' + e.message;
  }
}

async function fetchClusters() {
  try {
    const res = await fetch('/clusters/view');
    const data = await res.json();
    const dist = data.distribution || {};
    const labels = Object.keys(dist).map(k => 'Cluster ' + k);
    const values = Object.values(dist);

    if (clusterChart) clusterChart.destroy();
    const ctx = document.getElementById('clusterChart').getContext('2d');
    clusterChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Entries',
          data: values,
          backgroundColor: 'rgba(88,166,255,0.6)',
          borderColor: 'rgba(88,166,255,1)',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#30363d' } },
          y: { ticks: { color: '#8b949e' }, grid: { color: '#30363d' }, beginAtZero: true }
        }
      }
    });
  } catch(e) { /* clusters not ready yet */ }
}

async function doSearch() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  const res = document.getElementById('chat-result');
  res.style.display = 'block';
  res.innerHTML = '⏳ Searching...';
  try {
    const r = await fetch('/knowledge/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ query: q, top_k: 5 })
    });
    const data = await r.json();
    if (!data.chunks || data.chunks.length === 0) {
      res.innerHTML = '<span style="color:var(--red)">No matching knowledge found.</span>';
      return;
    }
    let html = `<b>Top results</b> (max similarity: ${data.max_score}):<br><br>`;
    data.chunks.forEach((c, i) => {
      html += `<b>${i+1}. ${c.title}</b> <span class="source-tag">${c.category}</span> <span class="source-tag">score: ${c.score}</span><br>`;
      html += `<span style="color:var(--text-muted)">${c.source}</span><br>`;
      html += c.content.substring(0, 300) + (c.content.length > 300 ? '...' : '') + '<br><br>';
    });
    res.innerHTML = html;
  } catch(e) {
    res.innerHTML = '<span style="color:var(--red)">Error: ' + e.message + '</span>';
  }
}

async function doChat() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  const res = document.getElementById('chat-result');
  res.style.display = 'block';
  res.innerHTML = '⏳ Querying Llama3 (this may take a moment)...';
  try {
    const r = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ query: q })
    });
    const data = await r.json();
    let html = '';
    if (data.refused) {
      html = '<span style="color:var(--red)">🚫 ' + data.answer + '</span>';
    } else {
      html = '<b>Answer:</b><br>' + data.answer.replace(/\n/g, '<br>') + '<br><br>';
      html += '<b>Sources:</b><br>';
      (data.sources || []).forEach(s => {
        html += `<span class="source-tag">${s.title}</span> `;
      });
      html += `<br><span class="log-info">Similarity: ${data.similarity_score} | Latency: ${data.latency_ms}ms</span>`;
    }
    res.innerHTML = html;
  } catch(e) {
    res.innerHTML = '<span style="color:var(--red)">Error: ' + e.message + '</span>';
  }
}

document.getElementById('search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

function formatUptime(s) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return (h > 0 ? h + 'h ' : '') + (m > 0 ? m + 'm ' : '') + sec + 's';
}

// Poll every 5 seconds
fetchMetrics();
fetchClusters();
setInterval(fetchMetrics, 5000);
setInterval(fetchClusters, 15000);
</script>
</body>
</html>"""
