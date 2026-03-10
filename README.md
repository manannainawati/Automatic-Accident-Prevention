# 🛡️ Automatic Accident Prevention System

A comprehensive IoT-based system that detects driver drowsiness, health emergencies, and vehicle crashes using ESP32 with multiple sensors. Automatically stops the vehicle and alerts authorities with GPS location.

## 🏗 Architecture

```
ESP32 + Sensors  ──►  Flask Backend  ──►  Twilio SMS / Email
                         ▲                to Authorities
Face Detection  ─────────┘
```

## 📦 Hardware Required

| Component | Purpose |
|:---|:---|
| ESP32 DevKit V1 | Main controller + WiFi |
| MAX30102 | Heart rate + SpO2 monitoring |
| MPU6050 | Accelerometer + Gyroscope (crash/tilt detection) |
| GPS NEO-6M | Real-time location tracking |
| Buzzer | Audible alert |
| LED | Visual warning indicator |
| 100 RPM Gear Motor | Simulates vehicle motor (stop/go) |
| L298N Motor Driver | Motor control interface |
| Breadboard + Wires | Prototyping connections |

## 🚀 Quick Setup

### 1. Hardware Assembly

Follow the wiring guide: [`docs/wiring_diagram.md`](docs/wiring_diagram.md)

### 2. Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
copy .env.example .env
# Edit .env with your Twilio credentials, email settings, etc.

# Run the server
python app.py
```

The dashboard will be available at: **http://localhost:5000/dashboard**

### 3. ESP32 Firmware Upload

1. Open `esp32_firmware/accident_prevention_system.ino` in **Arduino IDE**
2. Install required board: **ESP32 by Espressif** (via Board Manager)
3. Install libraries (via Library Manager):
   - `MAX30105` by SparkFun
   - `Adafruit MPU6050`
   - `TinyGPSPlus` by Mikal Hart
   - `ArduinoJson` by Benoit Blanchon
4. **Edit the configuration** in the `.ino` file:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* SERVER_URL    = "http://YOUR_PC_IP:5000";
   ```
5. Select board: **ESP32 Dev Module**
6. Upload!

### 4. Face Detection Integration

Your existing face detection module should send HTTP POST requests to:

```
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
| POST | `/api/sensor-data` | Receive ESP32 sensor readings |
| POST | `/api/face-detection` | Receive face detection results |
| GET | `/api/status` | Current system status |
| GET | `/api/alerts` | Alert history |
| GET | `/api/sensor-history` | Sensor readings for charts |
| POST | `/api/emergency-stop` | Manual emergency stop |
| POST | `/api/reset` | Reset system to NORMAL |
| GET | `/api/esp32-command` | ESP32 polls for commands |

## 🔔 Alert System

| Level | Triggers | Actions |
|:---:|:---|:---|
| ✅ NORMAL | All readings safe | No action |
| ⚠️ WARNING | Slight HR anomaly, drowsiness signs | Buzzer + LED |
| 🔶 CRITICAL | Significant HR/SpO2 issues, impact | Warning SMS |
| 🚨 EMERGENCY | Severe crash, driver unconscious, cardiac event | **Motor stop + SMS + Email to authorities with GPS** |

## 📁 Project Structure

```
├── esp32_firmware/
│   └── accident_prevention_system.ino    # ESP32 Arduino sketch
├── backend/
│   ├── app.py                            # Flask API server
│   ├── config.py                         # Configuration & thresholds
│   ├── models.py                         # Database models
│   ├── decision_engine.py                # Alert logic engine
│   ├── alert_service.py                  # SMS + Email notifications
│   ├── requirements.txt                  # Python dependencies
│   ├── .env.example                      # Environment variable template
│   ├── templates/dashboard.html          # Dashboard UI
│   └── static/                           # CSS + JS assets
├── dataset/
│   ├── heart_rate_thresholds.json        # HR/SpO2 threshold config
│   ├── mpu6050_thresholds.json           # Motion threshold config
│   ├── sample_sensor_data.csv            # Simulated sensor data
│   └── README.md                         # Dataset docs
├── docs/
│   ├── wiring_diagram.md                 # Hardware wiring guide
│   └── system_architecture.md            # System overview
└── README.md                             # This file
```

## ⚙️ Configuration

All thresholds are configurable in `backend/config.py`:

- Heart rate ranges (normal, warning, critical, emergency)
- SpO2 thresholds
- Acceleration impact detection levels
- Drowsiness score thresholds
- Alert cooldown timers

## 📜 License

This project is for educational and research purposes.
