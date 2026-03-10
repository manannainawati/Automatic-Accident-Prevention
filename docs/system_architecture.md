# System Architecture — Accident Prevention System

## Overview

The system uses a multi-layer architecture with local (ESP32) and remote (backend server) processing to ensure both fast emergency response and intelligent decision-making.

```
                    ┌───────────────────────────────────┐
                    │      FACE DETECTION MODULE        │
                    │   (Python / OpenCV / MediaPipe)   │
                    └────────────┬──────────────────────┘
                                 │ POST /api/face-detection
                                 ▼
┌──────────────┐    HTTP    ┌─────────────────────┐    SMS/Email    ┌────────────┐
│   ESP32 +    │──────────►│   Flask Backend      │──────────────►│ Authorities│
│   Sensors    │◄──────────│                      │                │ (Twilio)   │
│              │  Commands  │  ┌─────────────┐    │                └────────────┘
│ • MAX30102   │            │  │  Decision   │    │
│ • MPU6050    │            │  │   Engine    │    │    ┌────────────┐
│ • GPS NEO-6M │            │  └─────────────┘    │───►│ Dashboard  │
│ • Buzzer     │            │  ┌─────────────┐    │    │   (Web UI) │
│ • LED        │            │  │   SQLite    │    │    └────────────┘
│ • Motor      │            │  │  Database   │    │
└──────────────┘            │  └─────────────┘    │
                            └─────────────────────┘
```

## Data Flow

1. **ESP32** reads sensors every 2 seconds and sends JSON to backend via HTTP POST
2. **Backend** stores data, runs decision engine, and determines alert level
3. **Face detection module** (your existing system) sends drowsiness data independently
4. **Decision engine** combines sensor + face data for multi-factor analysis
5. On **EMERGENCY**: motor stops, buzzer activates, SMS + email sent to authorities with GPS
6. **Dashboard** polls backend every 2 seconds for real-time display

## Alert Levels

| Level | Trigger Examples | Actions |
|:---:|:---|:---|
| NORMAL | All readings within safe range | No action |
| WARNING | HR 101-120, SpO2 90-94%, harsh braking | Buzzer beep, LED blink |
| CRITICAL | HR 121-150, SpO2 80-89%, impact detected | Louder buzzer, warning SMS |
| EMERGENCY | HR >180, SpO2 <80%, severe crash, driver asleep | **Motor stop**, authority notification |

## Face Detection Integration

Your face detection module sends POST requests to `/api/face-detection`:

```json
{
    "drowsiness_score": 0.75,
    "eyes_closed": true,
    "eye_closure_duration_sec": 3.5,
    "yawn_detected": false,
    "yawn_count_last_min": 2,
    "head_pose_pitch": -15.0,
    "head_pose_yaw": 3.0,
    "face_detected": true,
    "confidence": 0.92
}
```
