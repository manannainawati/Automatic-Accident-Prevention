# Project Challenges & Technical Obstacles

During the development of the **Automatic Accident Prevention & Patient Monitoring System**, we encountered several critical technical challenges spanning hardware integration, backend scaling, and frontend rendering. Below is a comprehensive record of the problems we faced and how we architected solutions to overcome them.

## 1. Hardware & Sensor Integration (ESP32)
### The Problem: I2C Bus Contention and Synchronization
The system relies on multiple I2C-based sensors (MPU6050 for acceleration/crash detection and MAX30102 for heart rate/SpO2) operating simultaneously. Initially, polling both sensors at high frequencies caused the ESP32's I2C bus to hang, resulting in frozen readings or corrupted serial output. 
**The Solution:**
We implemented strict, non-blocking timing intervals for each sensor using `millis()` instead of `delay()`. We also separated the heavy interrupt-driven MAX30102 particle sensing logic from the MPU6050 FIFO buffer reads, ensuring neither sensor starved the I2C bus.

### The Problem: False Positives in Crash Detection
Standard road bumps or sharp turns triggered the $>4g$ acceleration threshold, resulting in false "Emergency" states and unnecessarily stopping the vehicle motor.
**The Solution:**
We added temporal logic inside the `decision_engine`—a true crash requires a sustained high-g spike alongside a sudden drop in speed (from the GPS data) rather than an isolated momentary spike from a pothole.

## 2. Frontend Real-Time Rendering (UI/UX)
### The Problem: Chart.js "Infinite Scroll" Memory Leak and Layout Stretching
To build the Live Dashboard and Patient Detail pages, we used `Chart.js` with responsive configurations (`maintainAspectRatio: false`). However, placing these canvases inside standard CSS Flexbox/Grid containers caused a recursive rendering loop. Chart.js would repeatedly trigger vertical resizing, pushing the page height out to thousands of pixels infinitely.
**The Solution:**
We isolated the canvas rendering engine by wrapping every `<canvas>` tag strictly within a `<div>` with `position: relative` and a fixed CSS `height: 300px;`. By removing `!important` tags on inline styles, Chart.js was forced to respect the hard boundary of the parent container, resulting in a stable, non-stretching UI.

### The Problem: Overcrowded Patient Vitals Layout
Initially, the Patient Detail page stacked heart rate, SpO2, readings count, and alert levels into a massive vertical column, burying the medical history PDF upload section below the fold.
**The Solution:**
We fundamentally restructured the HTML into a `display: grid` setup using `grid-template-columns: repeat(4, 1fr)` for vitals, placing all crucial metrics horizontally at the very top. Actions (Drag & Drop PDF, Simulate Data) were segregated into a neat 2-column grid beneath it.

## 3. Backend & Data Management (Python/Flask)
### The Problem: SQLite Database Locking Under High Telemetry Load
The ESP32 pushes sensor data (Heart Rate, SpO2, Accel, Speed) multiple times per second. Simultaneously, the frontend dashboard uses JavaScript `setInterval()` to fetch these readings via API. This concurrent read/write pressure caused `sqlite3.OperationalError: database is locked` errors.
**The Solution:**
We optimized the Flask-SQLAlchemy configuration by implementing connection pooling (`pool_size`, `max_overflow`), and enabled SQLite's Write-Ahead Logging (WAL) mode. We also batch SQL commits in the decision engine to reduce disk I/O frequency.

### The Problem: Medical History PDF Storage
Storing massive raw binaries (PDF files up to 16MB) directly into the `sqlite3` relational columns was drastically expanding the `.db` size and slowing down simple `SELECT` queries for the patient dashboard.
**The Solution:**
(Transitioning) We structured the API endpoints so that `LargeBinary` data could be efficiently streamed chunk-by-chunk to the client rather than loading the entire PDF into RAM at once, preventing the Flask server from running out of memory during downloads.

## 4. Systems Integration
### The Problem: Synchronizing ML Drowsiness with Hardware Telemetry
The machine learning component runs a heavy OpenCV loop to calculate Eye Aspect Ratio (EAR) for drowsiness scoring. Integrating this relatively slow (15-30 FPS) python loop with the high-speed (100+ Hz) ESP32 telemetry caused massive desyncs, where alerts were evaluating outdated drowsiness scores.
**The Solution:**
We pushed the drowsiness scores to a decoupled state-manager within the `DecisionEngine`. The ML model runs on a parallel background thread, updating a shared memory state, allowing the fast-running telemetry endpoint to always grab the "latest known" drowsiness score without waiting for the camera loop to finish.
