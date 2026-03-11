# 🛡️ AI-Powered Accident Prevention & Detection System

A comprehensive IoT and Telematics system that detects driver drowsiness, health emergencies, and vehicle crashes using an Arduino-based sensor suite. The system proactively stops the vehicle and alerts authorities with real-time GPS coordinates to ensure rapid response.

## 🏗 Architecture

```
Arduino + Sensors ──►  Core Engine  ──►  Twilio SMS / Email
                         (Python/Flask)         to Authorities
                         ▲
Face Detection  ─────────┘
```

## 📦 Hardware Required

| Component | Purpose |
|:---|:---|
| Arduino Uno | Main controller & Data Acquisition |
| WiFi Shield (e.g., ESP8266) | Remote connectivity for the Arduino |
| MAX30102 | Heart rate + SpO2 monitoring |
| MPU6050 | Accelerometer + Gyroscope (crash/tilt detection) |
| GPS NEO-6M | Real-time location tracking |
| Buzzer & LED | Audible and Visual alerting |
| 100 RPM Gear Motor | Simulates vehicle motor (stop/go) |
| L298N Motor Driver | Motor control interface |

## 🚀 Quick Setup

### 1. Hardware Assembly

Follow the standard wiring guide for the I2C sensors and the motor driver connected to your Arduino Uno.

### 2. Core Engine Setup (Backend)

The core logic handles thresholds, ML analytics integration, and dispatching alerts.

```bash
# Navigate to the core engine folder
cd core_engine

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate
# For Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
copy .env.example .env
# Edit .env with your Twilio credentials, email settings, etc.

# Run the server
python main.py
```

The live monitoring dashboard will be available at: **http://localhost:5000/dashboard**

### 3. Arduino Firmware Upload

1. Open `arduino_firmware/arduino_accident_prevention.ino` in the **Arduino IDE**.
2. Install required board files for the **Arduino Uno**.
3. Install required libraries (via Library Manager):
   - `MAX30105` by SparkFun
   - `Adafruit MPU6050`
   - `TinyGPSPlus` by Mikal Hart
   - `ArduinoJson` by Benoit Blanchon
4. **Configure network settings** in the `.ino` file:
   ```cpp
   const char* SERVER_URL = "http://YOUR_PC_IP:5000";
   // Add your WiFi Shield SSID and Password
   ```
5. Select board: **Arduino Uno**
6. Upload the sketch!

### 4. Face Detection Integration

The face detection module sends active HTTP POST requests to track drowsiness and attention.

```http
POST http://YOUR_PC_IP:5000/api/face-detection
Content-Type: application/json

{
    "drowsiness_score": 0.3,
    "eyes_closed": false,
    "eye_closure_duration_sec": 0.0,
    "yawn_detected": false,
    "yawn_count_last_min": 0,
    "face_detected": true,
    "confidence": 0.95
}
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|:---:|:---|:---|
| POST | `/api/sensor-data` | Receive Arduino sensor telemetry |
| POST | `/api/face-detection` | Receive facial analytics results |
| GET | `/api/status` | Current system health and status |
| GET | `/api/alerts` | Alert log history |
| GET | `/api/sensor-history` | Sensor metrics for dashboard charts |
| POST | `/api/emergency-stop` | Manual emergency stop trigger |
| POST | `/api/reset` | Reset system state to NORMAL |

## 🔔 Alert System

| Level | Triggers | Actions |
|:-----:|:--------:|:-------:|
| ✅ NORMAL | All readings stable | Passive Monitoring |
| ⚠️ WARNING | Minor HR anomalies, drowsiness signs | Buzzer + LED Warning |
| 🔶 CRITICAL | Major HR/SpO2 fluctuations, harsh braking | Warning SMS Dispatch |
| 🚨 EMERGENCY | Severe crash (MPU6050), driver blackout | **Motor stop + SMS/Email to authorities with GPS** |

## 📁 System Structure

```
├── arduino_firmware/
│   └── arduino_accident_prevention.ino   # Main Arduino sketch
├── core_engine/
│   ├── main.py                           # Flask API server
│   ├── config.py                         # Thresholds & Constraints
│   ├── models.py                         # DB Models
│   ├── decision_engine.py                # Core alert logic engine
│   ├── alert_service.py                  # Twilio SMS + Email service
│   ├── requirements.txt                  # Python dependencies
│   ├── .env.example                      # ENV templates
│   ├── templates/dashboard.html          # Dashboard UI
│   └── static/                           # CSS + JS assets
├── dataset/
│   ├── heart_rate_thresholds.json        # HR definitions
│   ├── mpu6050_thresholds.json           # Motion definitions
│   └── sample_sensor_data.csv            # Simulated testing data
└── README.md                             # Global instructions
```

## ⚙️ Configuration
All behavioral thresholds are configurable via `core_engine/config.py`:
- Biometric limits (Heart rate: normal, warning, critical)
- Inertial impact forces (G-force acceleration triggers)
- Drowsiness limits and cooldown timers

## 📜 License
This system is developed for research and educational purposes.
