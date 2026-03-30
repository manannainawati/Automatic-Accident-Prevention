/**
 * Accident Prevention System — Dashboard JavaScript
 * Real-time data fetching, Chart.js graphs, and UI updates.
 */

// ============================================================
// Configuration
// ============================================================

const API_BASE = window.location.origin;
const POLL_INTERVAL_MS = 2000;  // Fetch data every 2 seconds
const CHART_MAX_POINTS = 60;     // Show last 60 data points

// ============================================================
// Chart.js Setup
// ============================================================

Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;

// --- Vitals Chart (Heart Rate + SpO2) ---
const vitalsCtx = document.getElementById('chart-vitals').getContext('2d');
const vitalsChart = new Chart(vitalsCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Heart Rate (BPM)',
                data: [],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: 'y',
            },
            {
                label: 'SpO2 (%)',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4,
                yAxisID: 'y1',
            },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } },
        },
        scales: {
            x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 10 } },
            y: {
                type: 'linear', position: 'left',
                title: { display: true, text: 'BPM', color: '#ef4444' },
                min: 30, max: 200,
                grid: { color: 'rgba(255,255,255,0.04)' },
            },
            y1: {
                type: 'linear', position: 'right',
                title: { display: true, text: 'SpO2 %', color: '#3b82f6' },
                min: 70, max: 105,
                grid: { drawOnChartArea: false },
            },
        },
    },
});

// --- Acceleration Chart ---
const accelCtx = document.getElementById('chart-accel').getContext('2d');
const accelChart = new Chart(accelCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'X (g)',
                data: [],
                borderColor: '#10b981',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'Y (g)',
                data: [],
                borderColor: '#f59e0b',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'Z (g)',
                data: [],
                borderColor: '#8b5cf6',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } },
        },
        scales: {
            x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 10 } },
            y: {
                title: { display: true, text: 'Acceleration (g)' },
                grid: { color: 'rgba(255,255,255,0.04)' },
            },
        },
    },
});

// --- Gyroscope Chart ---
const gyroCtx = document.getElementById('chart-gyro').getContext('2d');
const gyroChart = new Chart(gyroCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'X (°/s)',
                data: [],
                borderColor: '#06b6d4',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'Y (°/s)',
                data: [],
                borderColor: '#ec4899',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'Z (°/s)',
                data: [],
                borderColor: '#f97316',
                borderWidth: 1.5,
                tension: 0.3,
                pointRadius: 0,
                fill: false,
            },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } },
        },
        scales: {
            x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 10 } },
            y: {
                title: { display: true, text: 'Angular Velocity (°/s)' },
                grid: { color: 'rgba(255,255,255,0.04)' },
            },
        },
    },
});

// ============================================================
// Data Fetching
// ============================================================

async function fetchStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        updateDashboard(data);
        updateConnectionStatus(true);
    } catch (err) {
        console.error('Failed to fetch status:', err);
        updateConnectionStatus(false);
    }
}

async function fetchSensorHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/sensor-history?limit=${CHART_MAX_POINTS}`);
        const data = await response.json();
        updateCharts(data.readings);
    } catch (err) {
        console.error('Failed to fetch sensor history:', err);
    }
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${API_BASE}/api/alerts?limit=20`);
        const data = await response.json();
        updateAlertsList(data.alerts);
    } catch (err) {
        console.error('Failed to fetch alerts:', err);
    }
}

// ============================================================
// Dashboard Updates
// ============================================================

function updateDashboard(data) {
    const sensor = data.latest_sensor;
    const face = data.latest_face;
    const evaluation = data.latest_evaluation;
    const status = data.system_status;

    if (!status) return;

    // -- Update status cards --
    if (sensor) {
        updateCard('heart-rate', sensor.heart_rate_bpm, evaluation?.heart_rate_status);
        updateCard('spo2', sensor.spo2_percent, evaluation?.spo2_status);
        updateCard('speed', sensor.speed_kmh, evaluation?.motion_status);

        // Update GPS
        if (sensor.latitude && sensor.longitude) {
            document.getElementById('gps-coords').textContent =
                `Lat: ${sensor.latitude.toFixed(6)}, Lng: ${sensor.longitude.toFixed(6)}`;
            updateMap(sensor.latitude, sensor.longitude);
        }
    }

    if (face) {
        const drowsyVal = face.drowsiness_score != null ?
            (face.drowsiness_score * 100).toFixed(0) + '%' : '--';
        document.getElementById('val-drowsiness').textContent = drowsyVal;
        updateCardStatus('drowsiness', evaluation?.drowsiness_status || 'OK');
    }

    // Motor status
    document.getElementById('val-motor').textContent = status.motor_running ? 'RUNNING' : 'STOPPED';
    document.getElementById('val-motor').style.fontSize = '18px';
    updateCardStatus('motor', status.motor_running ? 'OK' : 'STOPPED');
    if (!status.motor_running) {
        document.getElementById('card-motor').classList.add('emergency');
    } else {
        document.getElementById('card-motor').classList.remove('emergency');
    }

    // Alert level
    const alertLevel = status.current_alert_level || 'NORMAL';
    document.getElementById('val-alert-level').textContent = alertLevel;
    document.getElementById('val-alert-level').style.fontSize = '20px';
    updateAlertBanner(alertLevel, evaluation?.reasons || []);
    updateAlertLevelCard(alertLevel);
}

function updateCard(name, value, status) {
    const valEl = document.getElementById(`val-${name}`);
    if (valEl) {
        valEl.textContent = value != null ? (typeof value === 'number' ? value.toFixed(0) : value) : '--';
    }
    updateCardStatus(name, status || 'OK');
}

function updateCardStatus(name, status) {
    const statusEl = document.getElementById(`status-${name}`);
    const cardEl = document.getElementById(`card-${name}`);
    if (!statusEl || !cardEl) return;

    statusEl.textContent = status;
    statusEl.className = 'card-status';
    cardEl.className = 'card status-card';

    const levelMap = {
        'OK': '', 'NORMAL': '', 'AWAKE': '', 'RUNNING': '',
        'NO_READING': 'warning', 'LOW': 'warning', 'HIGH': 'warning',
        'SLIGHTLY_LOW': 'warning', 'HARSH_BRAKE': 'warning', 'DROWSY': 'warning',
        'CRITICAL_LOW': 'critical', 'CRITICAL_HIGH': 'critical',
        'CRITICAL': 'critical', 'IMPACT': 'critical', 'SPIN': 'critical',
        'VERY_DROWSY': 'critical', 'SUDDEN_CHANGE': 'critical',
        'EMERGENCY_HIGH': 'emergency', 'EMERGENCY': 'emergency',
        'SEVERE_CRASH': 'emergency', 'ROLLOVER': 'emergency',
        'ASLEEP': 'emergency', 'STOPPED': 'emergency',
    };

    const level = levelMap[status] || '';
    if (level) {
        statusEl.classList.add(level);
        cardEl.classList.add(level);
    }
}

function updateAlertLevelCard(alertLevel) {
    const cardEl = document.getElementById('card-alert-level');
    const statusEl = document.getElementById('status-alert');
    if (!cardEl || !statusEl) return;

    cardEl.className = 'card status-card';
    statusEl.className = 'card-status';
    statusEl.textContent = alertLevel;

    const level = alertLevel.toLowerCase();
    if (level !== 'normal') {
        cardEl.classList.add(level);
        statusEl.classList.add(level);
    }
}

function updateAlertBanner(alertLevel, reasons) {
    const banner = document.getElementById('alert-banner');
    const levelText = document.getElementById('alert-level-text');
    const reasonText = document.getElementById('alert-reason-text');
    const timeText = document.getElementById('alert-time');

    if (alertLevel === 'NORMAL') {
        banner.classList.add('hidden');
        return;
    }

    banner.classList.remove('hidden');
    banner.className = `alert-banner level-${alertLevel.toLowerCase()}`;
    levelText.textContent = alertLevel;
    reasonText.textContent = reasons.length > 0 ? reasons[0] : '';
    timeText.textContent = new Date().toLocaleTimeString();
}

function updateMap(lat, lng) {
    const iframe = document.getElementById('gps-map');
    const newSrc = `https://www.google.com/maps/embed/v1/place?key=AIzaSyAV7_ckPLPvVl02H2wiD2ohB6NInFZSjpg&q=${lat},${lng}&zoom=15`;
    if (iframe.src !== newSrc) {
        iframe.src = newSrc;
    }
}

function updateConnectionStatus(connected) {
    const el = document.getElementById('connection-status');
    const text = el.querySelector('.status-text');
    if (connected) {
        el.classList.remove('disconnected');
        text.textContent = 'Connected';
    } else {
        el.classList.add('disconnected');
        text.textContent = 'Disconnected';
    }
}

// ============================================================
// Charts Update
// ============================================================

function updateCharts(readings) {
    if (!readings || readings.length === 0) return;

    const labels = readings.map(r => {
        const d = new Date(r.timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    // Vitals chart
    vitalsChart.data.labels = labels;
    vitalsChart.data.datasets[0].data = readings.map(r => r.heart_rate_bpm);
    vitalsChart.data.datasets[1].data = readings.map(r => r.spo2_percent);
    vitalsChart.update('none');

    // Acceleration chart
    accelChart.data.labels = labels;
    accelChart.data.datasets[0].data = readings.map(r => r.accel_x);
    accelChart.data.datasets[1].data = readings.map(r => r.accel_y);
    accelChart.data.datasets[2].data = readings.map(r => r.accel_z);
    accelChart.update('none');

    // Gyroscope chart
    gyroChart.data.labels = labels;
    gyroChart.data.datasets[0].data = readings.map(r => r.gyro_x);
    gyroChart.data.datasets[1].data = readings.map(r => r.gyro_y);
    gyroChart.data.datasets[2].data = readings.map(r => r.gyro_z);
    gyroChart.update('none');
}

// ============================================================
// Alerts List
// ============================================================

function updateAlertsList(alerts) {
    const container = document.getElementById('alerts-list');
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="alert-empty">No alerts yet</div>';
        return;
    }

    container.innerHTML = alerts.map(alert => {
        const time = new Date(alert.timestamp).toLocaleTimeString();
        const levelClass = alert.alert_level.toLowerCase();
        return `
            <div class="alert-item level-${levelClass}">
                <span class="alert-item-level ${levelClass}">${alert.alert_level}</span>
                <span class="alert-item-message">${alert.message}</span>
                <span class="alert-item-time">${time}</span>
            </div>
        `;
    }).join('');
}

// ============================================================
// System Log
// ============================================================

function addLogEntry(message, level = 'info') {
    const log = document.getElementById('system-log');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry log-${level}`;
    entry.textContent = `[${time}] ${message}`;
    log.prepend(entry);

    // Keep max 50 entries
    while (log.children.length > 50) {
        log.removeChild(log.lastChild);
    }
}

// ============================================================
// User Actions
// ============================================================

async function triggerEmergencyStop() {
    if (!confirm('⛔ Are you sure you want to trigger EMERGENCY STOP?\n\nThis will:\n- Stop the motor\n- Activate buzzer\n- Notify authorities')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/emergency-stop`, { method: 'POST' });
        const data = await response.json();
        addLogEntry('EMERGENCY STOP TRIGGERED BY OPERATOR', 'emergency');
        fetchStatus();
        fetchAlerts();
    } catch (err) {
        console.error('Emergency stop failed:', err);
        addLogEntry(`Emergency stop failed: ${err.message}`, 'emergency');
    }
}

async function resetSystem() {
    if (!confirm('🔄 Reset system to NORMAL state?\n\nThis will re-enable the motor and clear alerts.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
        const data = await response.json();
        addLogEntry('System reset to NORMAL', 'info');
        fetchStatus();
    } catch (err) {
        console.error('Reset failed:', err);
        addLogEntry(`System reset failed: ${err.message}`, 'critical');
    }
}

// ============================================================
// Polling Loop
// ============================================================

function startPolling() {
    addLogEntry('Dashboard started. Polling for data...', 'info');

    // Initial fetch
    fetchStatus();
    fetchSensorHistory();
    fetchAlerts();

    // Periodic updates
    setInterval(fetchStatus, POLL_INTERVAL_MS);
    setInterval(fetchSensorHistory, POLL_INTERVAL_MS * 2.5);
    setInterval(fetchAlerts, POLL_INTERVAL_MS * 5);
}

// Start when page loads
document.addEventListener('DOMContentLoaded', startPolling);
