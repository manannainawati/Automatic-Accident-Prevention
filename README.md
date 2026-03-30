# Automatic Accident Prevention & Patient Monitoring System

A comprehensive IoT and Web monitoring system designed to detect accidents, monitor driver drowsiness, and manage patient medical history. It integrates ESP32 hardware sensors with a real-time Python Flask dashboard and patient management REST API.

---

## 🚀 Key Features

### 1. Hardware-Level Monitoring (ESP32)
*   **Crash Detection:** Uses MPU6050 Accelerometer & Gyroscope to detect sudden impacts. Thresholds > 4g trigger emergency stops.
*   **Health Monitoring:** Uses MAX30102 to monitor live Heart Rate and Blood Oxygen (SpO2).
*   **Location Tracking:** Integrates GPS NEO-6M to send precise coordinates of incidents.
*   **Drowsiness Detection:** Camera-based ML model analyzes eye closure/drowsiness scores.
*   **Actuators:** Automatically stops DC Motor, triggers an alarm buzzer, and activates LED warnings during critical conditions.

### 2. Live Global Dashboard
*   **Real-time Vitals:** Live Chart.js graphs tracking Heart Rate, SpO2, and Acceleration.
*   **System Status:** Centralized view of Motor status (Running/Stopped), Global Alert Level (Normal/Warning/Critical/Emergency), and recent system logs.
*   **Live Map:** Embedded GPS tracking for immediate response.

### 3. Patient Management System
*   **Comprehensive Profiles:** Register and manage patients (Age, Gender, Blood Group, Emergency Contacts).
*   **Individual Monitoring:** Dedicated live heartbeat and SpO2 monitor per patient.
*   **Simulation & Testing:** Built-in tools for testing specific scenarios (Normal, Warning, Critical, Emergency).
*   **Medical History (PDFs):** Secure drag-and-drop storage for patient medical histories using SQLite BLOB storage, integrated directly into the web interface.

---

## ⚠️ Alert Levels & Thresholds

The core **Decision Engine** evaluates streaming data and flags 4 distinct levels:
1.  **NORMAL:** HR (60-100 BPM), SpO2 (≥95%), Accel (<2g)
2.  **WARNING:** Elevated/Lowered HR, SpO2 (90-95%)
3.  **CRITICAL:** Dangerous HR (<40 or >150), SpO2 (80-90%), High Drowsiness score
4.  **EMERGENCY:** Heart Attack indicators (HR >180, SpO2 <70%), Crash detected (Accel >4g).
    *   *System Action:* Motor stopped automatically, Buzzer triggered, GPS Coordinates acquired, SMS + Email sent to authorities.

---

## 🛠️ Tech Stack & Architecture

*   **Hardware:** ESP32, MAX30102 (Pulse Oximeter), MPU6050 (IMU), GPS NEO-6M, DC Motor, Buzzer.
*   **Backend:** Python 3, Flask framework, SQLite3 (Database storage for patients and telemetry).
*   **Frontend HTML/CSS/JS:** Custom "Dark Glassmorphism" UI, Vanilla Javascript, Chart.js (for real-time visualizations).

---

## 💾 Installation & Setup

### Prerequisites
1.  Python 3.8+ installed on your machine.
2.  Arduino IDE configured for ESP32.

### Step-by-Step Backend Setup
1.  Navigate into the `core_engine` directory.
    ```bash
    cd core_engine
    ```
2.  Install required Python packages:
    ```bash
    pip install flask werkzeug
    ```
3.  Run the Flask Application:
    ```bash
    python main.py
    ```
    *The database (`instance/accident_prevention.db`) and necessary tables will automatically structure themselves upon the first run.*
4.  Access the Web Interface:
    *   **Dashboard:** `http://localhost:5000/dashboard`
    *   **Patient Manager:** `http://localhost:5000/patients`

### API Endpoints Overview
*   `GET /api/patients` - List all registered patients
*   `GET /api/patients/<id>/readings` - Fetch all saved sensor readings for a patient
*   `GET /api/patients/<id>/medical-history` - Fetch uploaded medical PDF records
*   `POST /api/sensor-data` - Push raw ESP32 telemetry to the decision engine

---

## 📸 Interface Previews

**Patient Management Interface**
A comprehensive detail page showing 4-grid vitals, fixed-height live tracking charts (BPM and SpO2), quick simulation tools, and PDF Drag&Drop areas.

**Global Dashboard**
A command-center-style UI showing aggregated telemetry, map tracking, and alert logs across the entire system.

---

## 🛡️ License
MIT License. Created for the Automatic Accident Prevention System project (2026).
