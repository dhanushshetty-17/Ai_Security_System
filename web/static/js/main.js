// Update system time
function updateTime() {
    const now = new Date();
    document.getElementById('sys-time').textContent = now.toLocaleString();
}
setInterval(updateTime, 1000);
updateTime();

// Security utility
function escapeHtml(unsafe) {
    return (unsafe || "").toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Audio Context for beep
let audioCtx = null;
let webAlarmsEnabled = localStorage.getItem('webAlarmsEnabled') === 'true';

if (webAlarmsEnabled) {
    const btn = document.getElementById('enable-audio-btn');
    if (btn) {
        btn.textContent = '🔊 Web Alarms Enabled';
        btn.style.background = 'rgba(76, 175, 80, 0.2)';
        btn.style.borderColor = '#4caf50';
    }
}

document.getElementById('enable-audio-btn')?.addEventListener('click', (e) => {
    if (webAlarmsEnabled) {
        webAlarmsEnabled = false;
        localStorage.setItem('webAlarmsEnabled', 'false');
        e.target.textContent = '🔇 Enable Web Alarms';
        e.target.style.background = 'rgba(255,255,255,0.1)';
        e.target.style.borderColor = 'var(--border-color)';
    } else {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        webAlarmsEnabled = true;
        localStorage.setItem('webAlarmsEnabled', 'true');
        e.target.textContent = '🔊 Web Alarms Enabled';
        e.target.style.background = 'rgba(76, 175, 80, 0.2)';
        e.target.style.borderColor = '#4caf50';
        playBeep(); // test beep
    }
});

function playBeep() {
    if (!webAlarmsEnabled) return;
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume().catch(e => console.log(e));
    }
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    oscillator.type = 'square';
    oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
    gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
    
    oscillator.start();
    gainNode.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.5);
    oscillator.stop(audioCtx.currentTime + 0.5);
}

// Chart Instance
let threatChart = null;

function initChart() {
    const ctx = document.getElementById('threatChart');
    if (!ctx) return;
    
    threatChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Low', 'Medium', 'High', 'Critical'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: ['#2e7d32', '#a66f00', '#b3261e', '#7f0000'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: 'white' } }
            }
        }
    });
}
initChart();

// Set to keep track of seen events so we don't beep twice for the same event
const seenEvents = new Set();

// Poll for events and status
async function pollData() {
    try {
        const response = await fetch('/api/events');
        if (response.status === 401) {
            // Session expired
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        // Update camera statuses
        data.statuses.forEach(status => {
            const ind = document.getElementById(`status-${status.camera_id}`);
            const fps = document.getElementById(`fps-${status.camera_id}`);
            
            if (ind && fps) {
                if (status.connected) {
                    ind.classList.add('connected');
                } else {
                    ind.classList.remove('connected');
                }
                fps.textContent = `FPS: ${status.fps.toFixed(1)}`;
            }
        });
        
        // System Health
        if (data.sys_health) {
            document.getElementById('cpu-usage').textContent = data.sys_health.cpu;
            document.getElementById('ram-usage').textContent = data.sys_health.ram;
        }
        
        // System Status
        if (data.current_threat_level) {
            const badge = document.getElementById('overall-threat');
            badge.className = 'badge ' + data.current_threat_level;
            badge.textContent = data.current_threat_level;
        }

        // Update event table and chart
        const tbody = document.getElementById('events-tbody');
        if (data.events.length > 0) {
            tbody.innerHTML = '';
            
            let counts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
            
            data.events.forEach(evt => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                tr.className = 'event-row';
                
                tr.onclick = () => {
                    document.getElementById('snapshot-modal').style.display = 'flex';
                    if (evt.snapshot_path) {
                        // Backend serves snapshots at /snapshots/{filename}
                        // We just need the basename
                        const filename = evt.snapshot_path.split(/[\/\\]/).pop();
                        document.getElementById('modal-img').src = '/snapshots/' + filename;
                        document.getElementById('modal-img').style.display = 'block';
                        document.getElementById('modal-no-img').style.display = 'none';
                    } else {
                        document.getElementById('modal-img').style.display = 'none';
                        document.getElementById('modal-no-img').style.display = 'block';
                    }
                };
                
                // Format timestamp
                const date = new Date(evt.timestamp * 1000);
                
                // Create badge for threat level
                const lvlClass = evt.threat_level || 'LOW';
                const badge = `<span class="badge ${lvlClass}">${lvlClass}</span>`;
                
                counts[lvlClass] = (counts[lvlClass] || 0) + 1;
                
                // Play sound if new high/critical threat
                if ((lvlClass === 'HIGH' || lvlClass === 'CRITICAL') && !seenEvents.has(evt.event_id)) {
                    playBeep();
                }
                seenEvents.add(evt.event_id);
                
                tr.innerHTML = `
                    <td>${date.toLocaleTimeString()}</td>
                    <td>${escapeHtml(evt.camera_id)}</td>
                    <td>${escapeHtml(evt.label)}</td>
                    <td>${badge}</td>
                `;
                tbody.appendChild(tr);
            });
            
            // Update chart
            if (threatChart) {
                threatChart.data.datasets[0].data = [counts.LOW, counts.MEDIUM, counts.HIGH, counts.CRITICAL];
                threatChart.update();
            }
        }
        
    } catch (e) {
        console.error("Polling error:", e);
    }
}

// Fetch and render reports
async function fetchReports(query = "") {
    try {
        const url = query ? `/api/search?query=${encodeURIComponent(query)}` : '/api/reports';
        const response = await fetch(url);
        if (response.status === 401) return;
        
        const reports = await response.json();
        const container = document.getElementById('reports-container');
        
        if (reports.length === 0) {
            container.innerHTML = '<div style="color: var(--text-secondary);">No reports found.</div>';
            return;
        }
        
        container.innerHTML = '';
        reports.forEach(r => {
            const date = new Date(r.timestamp * 1000).toLocaleString();
            const card = document.createElement('div');
            card.style.cssText = 'background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-color);';
            
            let imgHtml = '';
            if (r.image_url) {
                imgHtml = `<img src="${r.image_url}" style="width: 100%; border-radius: 4px; margin-bottom: 0.5rem;">`;
            }
            
            card.innerHTML = `
                ${imgHtml}
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${date} • ${escapeHtml(r.camera_id)}</div>
                <h4 style="margin-bottom: 0.5rem; color: #ffeb3b;">${escapeHtml(r.threat_label)}</h4>
                <p style="font-size: 0.9rem; line-height: 1.4; color: #e2e8f0; white-space: pre-wrap;">${escapeHtml(r.ai_summary)}</p>
            `;
            container.appendChild(card);
        });
        
    } catch (e) {
        console.error("Failed to fetch reports:", e);
    }
}

// Set up search listener
document.getElementById('report-search').addEventListener('input', (e) => {
    fetchReports(e.target.value);
});

// Poll every 2 seconds
setInterval(pollData, 2000);
pollData();

// Fetch reports less frequently
setInterval(() => fetchReports(document.getElementById('report-search').value), 10000);
fetchReports();

// Heatmap controls
const heatmapToggleBtn = document.getElementById('heatmap-toggle-btn');
if (heatmapToggleBtn) {
    heatmapToggleBtn.addEventListener('click', async (e) => {
        try {
            const res = await fetch('/api/heatmap/toggle', { method: 'POST' });
            const data = await res.json();
            if (data.enabled) {
                e.target.textContent = '🔥 Heatmap ON';
                e.target.style.background = 'rgba(59, 130, 246, 0.2)';
                e.target.style.borderColor = '#3b82f6';
            } else {
                e.target.textContent = '⏸️ Heatmap OFF';
                e.target.style.background = 'rgba(255,255,255,0.1)';
                e.target.style.borderColor = 'var(--border-color)';
            }
        } catch (err) {
            console.error("Heatmap toggle failed", err);
        }
    });
}

const heatmapResetBtn = document.getElementById('heatmap-reset-btn');
if (heatmapResetBtn) {
    heatmapResetBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/heatmap/reset', { method: 'POST' });
            const originalText = heatmapResetBtn.innerHTML;
            heatmapResetBtn.innerHTML = '✅ Cleared';
            setTimeout(() => { heatmapResetBtn.innerHTML = originalText; }, 1500);
        } catch (err) {
            console.error("Heatmap reset failed", err);
        }
    });
}
