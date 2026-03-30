/**
 * Patients Module — JavaScript
 * CRUD operations, heartbeat chart, PDF upload, and simulation.
 */

const API = window.location.origin;
let allPatients = [];

// ============================================================
// Toast Notifications
// ============================================================

function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ============================================================
// Modal
// ============================================================

function openModal() {
    document.getElementById('modal-overlay').classList.add('open');
}

function closeModal(e) {
    if (e && e.target !== document.getElementById('modal-overlay')) return;
    document.getElementById('modal-overlay').classList.remove('open');
    document.getElementById('patient-form')?.reset();
}

// ============================================================
// Patients List Page
// ============================================================

async function loadPatients() {
    try {
        const res = await fetch(`${API}/api/patients`);
        const data = await res.json();
        allPatients = data.patients || [];
        renderPatients(allPatients);
        updateStats(allPatients);
    } catch (err) {
        console.error('Failed to load patients:', err);
    }
}

function renderPatients(patients) {
    const tbody = document.getElementById('patients-tbody');
    if (!tbody) return;

    if (patients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-row">No patients registered yet. Click "Register Patient" to add one.</td></tr>';
        return;
    }

    tbody.innerHTML = patients.map(p => {
        const date = new Date(p.created_at).toLocaleDateString();
        return `
            <tr>
                <td>#${p.id}</td>
                <td><a href="/patients/${p.id}" class="patient-link">${p.name}</a></td>
                <td>${p.age || '--'}</td>
                <td>${p.gender || '--'}</td>
                <td>${p.blood_group ? `<span class="badge badge-blood">${p.blood_group}</span>` : '--'}</td>
                <td>${p.contact_number || '--'}</td>
                <td>${p.readings_count}</td>
                <td>${p.files_count}</td>
                <td>${date}</td>
                <td>
                    <a href="/patients/${p.id}" class="btn btn-sm btn-view">View</a>
                    <button class="btn btn-sm btn-delete-sm" onclick="deletePatientFromList(${p.id}, '${p.name}')">✕</button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateStats(patients) {
    const totalEl = document.getElementById('stat-total');
    const readingsEl = document.getElementById('stat-readings');
    const filesEl = document.getElementById('stat-files');
    if (totalEl) totalEl.textContent = patients.length;
    if (readingsEl) readingsEl.textContent = patients.reduce((s, p) => s + (p.readings_count || 0), 0);
    if (filesEl) filesEl.textContent = patients.reduce((s, p) => s + (p.files_count || 0), 0);
}

function filterPatients() {
    const query = document.getElementById('search-input').value.toLowerCase();
    const filtered = allPatients.filter(p =>
        p.name.toLowerCase().includes(query) ||
        (p.blood_group || '').toLowerCase().includes(query) ||
        (p.contact_number || '').includes(query)
    );
    renderPatients(filtered);
}

async function submitPatient(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-submit');
    btn.querySelector('.btn-text').style.display = 'none';
    btn.querySelector('.btn-loading').style.display = 'inline';

    try {
        const body = {
            name: document.getElementById('f-name').value,
            age: parseInt(document.getElementById('f-age').value) || null,
            gender: document.getElementById('f-gender').value || null,
            blood_group: document.getElementById('f-blood').value || null,
            contact_number: document.getElementById('f-contact').value || null,
            emergency_contact: document.getElementById('f-emergency').value || null,
            address: document.getElementById('f-address').value || null,
            notes: document.getElementById('f-notes').value || null,
        };

        const res = await fetch(`${API}/api/patients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error((await res.json()).error || 'Failed');

        showToast('Patient registered successfully!');
        closeModal();
        loadPatients();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.querySelector('.btn-text').style.display = 'inline';
        btn.querySelector('.btn-loading').style.display = 'none';
    }
}

async function deletePatientFromList(id, name) {
    if (!confirm(`Delete patient "${name}"? This will remove all their readings and files.`)) return;
    try {
        await fetch(`${API}/api/patients/${id}`, { method: 'DELETE' });
        showToast('Patient deleted');
        loadPatients();
    } catch (err) {
        showToast('Delete failed', 'error');
    }
}

// ============================================================
// Patient Detail Page
// ============================================================

let heartbeatChart = null;
const CHART_MAX = 60;

function initHeartbeatChart() {
    const canvas = document.getElementById('chart-heartbeat');
    if (!canvas) return;

    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;

    const ctx = canvas.getContext('2d');
    heartbeatChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Heart Rate (BPM)',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#ef4444',
                    pointHoverRadius: 6,
                },
                {
                    label: 'SpO2 (%)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 2,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#3b82f6',
                    pointHoverRadius: 5,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 400 },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 20 },
                },
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: { maxTicksLimit: 10, font: { size: 10 } },
                },
                y: {
                    type: 'linear', position: 'left',
                    title: { display: true, text: 'Heart Rate (BPM)', color: '#ef4444' },
                    min: 30, max: 200,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                },
                y1: {
                    type: 'linear', position: 'right',
                    title: { display: true, text: 'SpO2 (%)', color: '#3b82f6' },
                    min: 70, max: 105,
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

async function loadReadings(patientId) {
    try {
        const res = await fetch(`${API}/api/patients/${patientId}/readings?limit=${CHART_MAX}`);
        const data = await res.json();
        const readings = data.readings || [];
        updateHeartbeatChart(readings);
        updateVitals(readings);
        renderReadingsTable(readings);
    } catch (err) {
        console.error('Failed to load readings:', err);
    }
}

function updateHeartbeatChart(readings) {
    if (!heartbeatChart || readings.length === 0) return;

    const labels = readings.map(r => {
        const d = new Date(r.timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    heartbeatChart.data.labels = labels;
    heartbeatChart.data.datasets[0].data = readings.map(r => r.heart_rate_bpm);
    heartbeatChart.data.datasets[1].data = readings.map(r => r.spo2_percent);
    heartbeatChart.update('none');
}

function updateVitals(readings) {
    const hrEl = document.getElementById('vital-hr-val');
    const spo2El = document.getElementById('vital-spo2-val');
    const alertEl = document.getElementById('vital-alert-val');
    const countEl = document.getElementById('vital-readings-val');

    if (readings.length > 0) {
        const latest = readings[readings.length - 1];
        if (hrEl) hrEl.textContent = latest.heart_rate_bpm != null ? Math.round(latest.heart_rate_bpm) : '--';
        if (spo2El) spo2El.textContent = latest.spo2_percent != null ? Math.round(latest.spo2_percent) : '--';
        if (alertEl) alertEl.textContent = latest.alert_level || 'NORMAL';

        // Sync heartbeat pulse speed to BPM
        const pulseEl = document.getElementById('heartbeat-pulse');
        if (pulseEl && latest.heart_rate_bpm) {
            const duration = Math.max(0.3, 60 / latest.heart_rate_bpm);
            pulseEl.style.animationDuration = duration + 's';
        }
    }
    if (countEl) countEl.textContent = readings.length;
}

function renderReadingsTable(readings) {
    const tbody = document.getElementById('readings-tbody');
    if (!tbody) return;

    if (readings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No readings yet. Add one using the form or simulate.</td></tr>';
        return;
    }

    const reversed = [...readings].reverse(); // newest first
    tbody.innerHTML = reversed.slice(0, 50).map(r => {
        const time = new Date(r.timestamp).toLocaleTimeString();
        const alertClass = (r.alert_level || 'normal').toLowerCase();
        return `
            <tr>
                <td>${time}</td>
                <td>${r.heart_rate_bpm != null ? r.heart_rate_bpm.toFixed(0) : '--'} BPM</td>
                <td>${r.spo2_percent != null ? r.spo2_percent.toFixed(0) : '--'}%</td>
                <td>${(r.accel_x||0).toFixed(2)} / ${(r.accel_y||0).toFixed(2)} / ${(r.accel_z||0).toFixed(2)}</td>
                <td>${r.speed_kmh != null ? r.speed_kmh.toFixed(0) : '--'} km/h</td>
                <td><span class="badge badge-${alertClass}">${r.alert_level || 'NORMAL'}</span></td>
            </tr>
        `;
    }).join('');
}

async function submitReading(e, patientId) {
    e.preventDefault();
    try {
        const body = {
            heart_rate_bpm: parseFloat(document.getElementById('r-hr').value) || null,
            spo2_percent: parseFloat(document.getElementById('r-spo2').value) || null,
            accel_x: parseFloat(document.getElementById('r-ax').value) || 0,
            accel_y: parseFloat(document.getElementById('r-ay').value) || 0,
            accel_z: parseFloat(document.getElementById('r-az').value) || -1,
            speed_kmh: parseFloat(document.getElementById('r-speed').value) || 0,
        };

        const res = await fetch(`${API}/api/patients/${patientId}/readings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error('Failed to submit reading');

        const result = await res.json();
        showToast(`Reading added — Alert: ${result.alert_level}`);
        loadReadings(patientId);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Simulation presets
const SIM_PRESETS = {
    normal:    { heart_rate_bpm: 72, spo2_percent: 98, accel_x: 0.05, accel_y: 0.08, accel_z: -0.98, speed_kmh: 45 },
    warning:   { heart_rate_bpm: 125, spo2_percent: 93, accel_x: 0.15, accel_y: -0.45, accel_z: -0.92, speed_kmh: 55 },
    critical:  { heart_rate_bpm: 155, spo2_percent: 85, accel_x: 0.8, accel_y: 1.2, accel_z: 0.5, speed_kmh: 30 },
    emergency: { heart_rate_bpm: 190, spo2_percent: 78, accel_x: 4.5, accel_y: 5.2, accel_z: 6.8, speed_kmh: 5 },
};

async function simulateReading(patientId, level) {
    const preset = SIM_PRESETS[level];
    // Add slight randomness
    const data = {
        heart_rate_bpm: preset.heart_rate_bpm + (Math.random() * 6 - 3),
        spo2_percent: Math.min(100, preset.spo2_percent + (Math.random() * 2 - 1)),
        accel_x: preset.accel_x + (Math.random() * 0.1 - 0.05),
        accel_y: preset.accel_y + (Math.random() * 0.1 - 0.05),
        accel_z: preset.accel_z + (Math.random() * 0.1 - 0.05),
        speed_kmh: preset.speed_kmh + (Math.random() * 4 - 2),
    };

    try {
        const res = await fetch(`${API}/api/patients/${patientId}/readings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error('Simulation failed');
        const result = await res.json();
        showToast(`Simulated ${level} reading — Alert: ${result.alert_level}`);
        loadReadings(patientId);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ============================================================
// PDF Upload
// ============================================================

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e, patientId) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0], patientId);
}

function handleFileSelect(e, patientId) {
    const files = e.target.files;
    if (files.length > 0) uploadFile(files[0], patientId);
    e.target.value = ''; // reset so same file can be selected again
}

async function uploadFile(file, patientId) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Only PDF files are accepted', 'error');
        return;
    }

    const progressEl = document.getElementById('upload-progress');
    const fillEl = document.getElementById('progress-fill');
    const textEl = document.getElementById('progress-text');
    progressEl.style.display = 'flex';
    fillEl.style.width = '30%';
    textEl.textContent = `Uploading ${file.name}...`;

    try {
        const formData = new FormData();
        formData.append('file', file);

        fillEl.style.width = '60%';

        const res = await fetch(`${API}/api/patients/${patientId}/medical-history`, {
            method: 'POST',
            body: formData,
        });

        fillEl.style.width = '90%';

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Upload failed');
        }

        fillEl.style.width = '100%';
        textEl.textContent = 'Upload complete!';
        showToast(`"${file.name}" uploaded successfully!`);

        setTimeout(() => {
            progressEl.style.display = 'none';
            fillEl.style.width = '0%';
        }, 1500);

        loadMedicalHistory(patientId);
    } catch (err) {
        showToast(err.message, 'error');
        progressEl.style.display = 'none';
        fillEl.style.width = '0%';
    }
}

async function loadMedicalHistory(patientId) {
    try {
        const res = await fetch(`${API}/api/patients/${patientId}/medical-history`);
        const data = await res.json();
        renderFilesList(data.files || [], patientId);
    } catch (err) {
        console.error('Failed to load files:', err);
    }
}

function renderFilesList(files, patientId) {
    const container = document.getElementById('files-list');
    if (!container) return;

    if (files.length === 0) {
        container.innerHTML = '<div class="files-empty">No medical records uploaded yet</div>';
        return;
    }

    container.innerHTML = files.map(f => {
        const date = new Date(f.uploaded_at).toLocaleDateString();
        const size = f.file_size ? formatBytes(f.file_size) : '--';
        return `
            <div class="file-item">
                <span class="file-icon">📄</span>
                <div class="file-info">
                    <div class="file-name">${f.filename}</div>
                    <div class="file-meta">${size} · ${date}</div>
                </div>
                <div class="file-actions">
                    <a href="${API}/api/patients/${patientId}/medical-history/${f.id}/download"
                       class="btn-icon btn-download" title="Download">⬇️</a>
                    <button class="btn-icon btn-delete-icon" title="Delete"
                            onclick="deleteMedicalFile(${patientId}, ${f.id}, '${f.filename}')">✕</button>
                </div>
            </div>
        `;
    }).join('');
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

async function deleteMedicalFile(patientId, fileId, filename) {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
        await fetch(`${API}/api/patients/${patientId}/medical-history/${fileId}`, { method: 'DELETE' });
        showToast('File deleted');
        loadMedicalHistory(patientId);
    } catch (err) {
        showToast('Delete failed', 'error');
    }
}

async function deletePatient(patientId) {
    if (!confirm('Delete this patient and all associated data?')) return;
    try {
        await fetch(`${API}/api/patients/${patientId}`, { method: 'DELETE' });
        showToast('Patient deleted');
        window.location.href = '/patients';
    } catch (err) {
        showToast('Delete failed', 'error');
    }
}

// ============================================================
// Page Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Patients list page
    if (document.getElementById('patients-table')) {
        loadPatients();
    }

    // Patient detail page
    if (typeof PATIENT_ID !== 'undefined') {
        initHeartbeatChart();
        loadReadings(PATIENT_ID);
        loadMedicalHistory(PATIENT_ID);

        // Polling for live updates
        setInterval(() => loadReadings(PATIENT_ID), 5000);
    }
});
