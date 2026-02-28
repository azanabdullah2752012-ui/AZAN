"""
AZAN RL Training Dashboard
Real-time visualization of training progress and knowledge base metrics
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AZAN RL Training Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
            background: rgba(255, 255, 255, 0.05);
            padding: 30px;
            border-radius: 10px;
            border-left: 5px solid #00d4ff;
        }
        
        h1 {
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .subtitle {
            color: #888;
            font-size: 1.1em;
        }
        
        .training-domains {
            margin-top: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .domain-badge {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid #00d4ff;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            color: #00d4ff;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 10px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }
        
        .card-title {
            color: #00d4ff;
            font-size: 1.2em;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.1);
        }
        
        .metric:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .metric-label {
            color: #aaa;
            font-size: 0.95em;
        }
        
        .metric-value {
            color: #00d4ff;
            font-weight: bold;
            font-size: 1.3em;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        button {
            flex: 1;
            padding: 12px 20px;
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 212, 255, 0.4);
        }
        
        button.danger {
            background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.active {
            background-color: #00ff00;
        }
        
        .status-indicator.inactive {
            background-color: #ff4444;
            animation: none;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .knowledge-section {
            grid-column: 1 / -1;
        }
        
        .knowledge-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .knowledge-item {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .knowledge-item-title {
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .knowledge-item-count {
            color: #888;
            font-size: 0.9em;
        }
        
        .search-section {
            grid-column: 1 / -1;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .search-box input {
            flex: 1;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 5px;
            color: #e0e0e0;
            font-size: 1em;
        }
        
        .search-box input::placeholder {
            color: #666;
        }
        
        .search-results {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 8px;
            padding: 20px;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .search-result-item {
            background: rgba(0, 212, 255, 0.05);
            border-left: 3px solid #00d4ff;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        
        .search-result-title {
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .search-result-source {
            color: #888;
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        
        .search-result-content {
            color: #ccc;
            font-size: 0.95em;
            line-height: 1.4;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 0.9em;
        }
        
        .error-message {
            background: rgba(255, 68, 68, 0.2);
            border: 1px solid #ff4444;
            color: #ff9999;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .success-message {
            background: rgba(0, 255, 0, 0.2);
            border: 1px solid #00ff00;
            color: #99ff99;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎓 AZAN RL Training Dashboard</h1>
            <p class="subtitle">Autonomous Learning from Curated Knowledge</p>
            <div class="training-domains">
                <span class="domain-badge">🏛️ Indian Constitution</span>
                <span class="domain-badge">🌍 UN Treaties</span>
                <span class="domain-badge">⚔️ Military Strategies</span>
                <span class="domain-badge">📊 Political Definitions</span>
            </div>
        </header>
        
        <div id="message-container"></div>
        
        <div class="dashboard">
            <!-- Training Status Card -->
            <div class="card">
                <div class="card-title">Training Status</div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span>
                        <span class="status-indicator active" id="status-indicator"></span>
                        <span id="status-text">Initializing...</span>
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Current Iteration</span>
                    <span class="metric-value" id="iteration">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Reward</span>
                    <span class="metric-value" id="total-reward">0.00</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Average Reward</span>
                    <span class="metric-value" id="avg-reward">0.00</span>
                </div>
                <div class="controls">
                    <button id="start-btn" onclick="startTraining()">Start Training</button>
                    <button class="danger" id="stop-btn" onclick="stopTraining()" disabled>Stop Training</button>
                </div>
            </div>
            
            <!-- Knowledge Metrics Card -->
            <div class="card">
                <div class="card-title">Knowledge Base</div>
                <div class="metric">
                    <span class="metric-label">Total Items</span>
                    <span class="metric-value" id="knowledge-items">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Q&A Pairs</span>
                    <span class="metric-value" id="qa-pairs">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Pairs Learned</span>
                    <span class="metric-value" id="pairs-learned">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sources</span>
                    <span class="metric-value" id="sources-count">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Categories</span>
                    <span class="metric-value" id="categories-count">0</span>
                </div>
                <div class="controls">
                    <button onclick="refreshStats()">Refresh Stats</button>
                </div>
            </div>
            
            <!-- Rewards Chart -->
            <div class="card">
                <div class="card-title">Reward Trend</div>
                <div class="chart-container">
                    <canvas id="rewards-chart"></canvas>
                </div>
            </div>
            
            <!-- Knowledge Items Distribution -->
            <div class="card">
                <div class="card-title">Knowledge Distribution</div>
                <div class="knowledge-grid" id="knowledge-grid"></div>
            </div>
            
            <!-- Knowledge Search Section -->
            <div class="card search-section">
                <div class="card-title">Search Knowledge Base</div>
                <div class="search-box">
                    <input type="text" id="search-query" placeholder="Search for Constitution, UN treaties, military strategy, etc.">
                    <button onclick="searchKnowledge()">Search</button>
                </div>
                <div id="search-results" class="search-results" style="display: none;"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>AZAN - Autonomous Zero-hallucination Autonomous Network | Real-time RL Training Dashboard</p>
            <p>Updates every 5 seconds • Data-only responses • Strict sourcing</p>
        </div>
    </div>
    
    <script>
        let rewardsChart = null;
        let autoRefreshInterval = null;
        
        function showMessage(message, type = 'info') {
            const container = document.getElementById('message-container');
            const messageClass = type === 'error' ? 'error-message' : 'success-message';
            container.innerHTML = `<div class="${messageClass}">${message}</div>`;
            setTimeout(() => {
                container.innerHTML = '';
            }, 5000);
        }
        
        async function fetchStatus() {
            try {
                const response = await fetch('/api/azan/rl/status');
                if (!response.ok) throw new Error('Failed to fetch status');
                
                const data = await response.json();
                
                document.getElementById('iteration').textContent = data.iteration;
                document.getElementById('total-reward').textContent = data.total_reward.toFixed(2);
                document.getElementById('avg-reward').textContent = data.avg_reward.toFixed(2);
                document.getElementById('pairs-learned').textContent = data.total_learned;
                
                const statusIndicator = document.getElementById('status-indicator');
                const statusText = document.getElementById('status-text');
                
                if (data.active) {
                    statusIndicator.className = 'status-indicator active';
                    statusText.textContent = 'Training Active';
                    document.getElementById('start-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = false;
                } else {
                    statusIndicator.className = 'status-indicator inactive';
                    statusText.textContent = 'Training Inactive';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                }
                
                // Update rewards chart
                if (data.recent_rewards && data.recent_rewards.length > 0) {
                    updateRewardsChart(data.recent_rewards);
                }
            } catch (error) {
                console.error('Error fetching status:', error);
                showMessage('Error fetching training status', 'error');
            }
        }
        
        async function refreshStats() {
            try {
                const response = await fetch('/api/azan/rl/knowledge-stats');
                if (!response.ok) throw new Error('Failed to fetch stats');
                
                const data = await response.json();
                
                document.getElementById('knowledge-items').textContent = data.total_items;
                document.getElementById('qa-pairs').textContent = data.total_qa_pairs;
                document.getElementById('sources-count').textContent = data.sources.length;
                document.getElementById('categories-count').textContent = data.categories.length;
                
                // Update knowledge grid
                const grid = document.getElementById('knowledge-grid');
                grid.innerHTML = '';
                
                // Add sources
                if (data.sources_detail) {
                    for (const [source, count] of Object.entries(data.sources_detail)) {
                        const item = document.createElement('div');
                        item.className = 'knowledge-item';
                        item.innerHTML = `
                            <div class="knowledge-item-title">${source}</div>
                            <div class="knowledge-item-count">${count} items</div>
                        `;
                        grid.appendChild(item);
                    }
                }
                
                showMessage('Stats refreshed', 'success');
            } catch (error) {
                console.error('Error refreshing stats:', error);
                showMessage('Error refreshing statistics', 'error');
            }
        }
        
        function updateRewardsChart(rewards) {
            const ctx = document.getElementById('rewards-chart').getContext('2d');
            
            const labels = rewards.map((_, i) => `Iter ${rewards[i].iteration}`);
            const data = rewards.map(r => r.reward);
            
            if (rewardsChart) {
                rewardsChart.data.labels = labels;
                rewardsChart.data.datasets[0].data = data;
                rewardsChart.update();
            } else {
                rewardsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Reward per Iteration',
                            data: data,
                            borderColor: '#00d4ff',
                            backgroundColor: 'rgba(0, 212, 255, 0.1)',
                            tension: 0.4,
                            fill: true,
                            pointBackgroundColor: '#00d4ff',
                            pointBorderColor: '#00d4ff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: { color: '#aaa' }
                            }
                        },
                        scales: {
                            y: {
                                ticks: { color: '#aaa' },
                                grid: { color: 'rgba(0, 212, 255, 0.1)' }
                            },
                            x: {
                                ticks: { color: '#aaa' },
                                grid: { color: 'rgba(0, 212, 255, 0.1)' }
                            }
                        }
                    }
                });
            }
        }
        
        async function startTraining() {
            try {
                const response = await fetch('/api/azan/rl/start', { method: 'POST' });
                const data = await response.json();
                showMessage(data.message, 'success');
                fetchStatus();
            } catch (error) {
                showMessage('Error starting training', 'error');
            }
        }
        
        async function stopTraining() {
            try {
                const response = await fetch('/api/azan/rl/stop', { method: 'POST' });
                const data = await response.json();
                showMessage(data.message, 'success');
                fetchStatus();
            } catch (error) {
                showMessage('Error stopping training', 'error');
            }
        }
        
        async function searchKnowledge() {
            const query = document.getElementById('search-query').value.trim();
            if (!query) {
                showMessage('Please enter a search query', 'error');
                return;
            }
            
            try {
                const response = await fetch(`/api/azan/search?query=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error('Search failed');
                
                const data = await response.json();
                const resultsDiv = document.getElementById('search-results');
                
                if (data.results && data.results.length > 0) {
                    resultsDiv.innerHTML = '';
                    data.results.forEach(result => {
                        const resultHTML = `
                            <div class="search-result-item">
                                <div class="search-result-title">${result.title}</div>
                                <div class="search-result-source">📚 ${result.source} | Category: ${result.category}</div>
                                <div class="search-result-content">${result.content}</div>
                                <div style="color: #666; font-size: 0.85em; margin-top: 8px;">
                                    Keywords: ${result.key_terms.join(', ')}
                                </div>
                            </div>
                        `;
                        resultsDiv.innerHTML += resultHTML;
                    });
                    resultsDiv.style.display = 'block';
                } else {
                    resultsDiv.innerHTML = '<p>No results found. Try searching for: Constitution, UN, military, diplomacy, etc.</p>';
                    resultsDiv.style.display = 'block';
                }
            } catch (error) {
                showMessage('Error searching knowledge base', 'error');
            }
        }
        
        // Initialize and start auto-refresh
        function initialize() {
            fetchStatus();
            refreshStats();
            
            // Auto-refresh every 5 seconds
            autoRefreshInterval = setInterval(() => {
                fetchStatus();
            }, 5000);
            
            // Allow Enter key in search
            document.getElementById('search-query').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') searchKnowledge();
            });
        }
        
        // Start on page load
        window.addEventListener('load', initialize);
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
        });
    </script>
</body>
</html>
"""

def get_dashboard():
    """Return dashboard HTML"""
    return DASHBOARD_HTML
