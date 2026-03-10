import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration with tunable thresholds."""

    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "accident-prevention-secret-key-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///accident_prevention.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Twilio SMS ---
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

    # --- Emergency Contacts ---
    EMERGENCY_PHONE_NUMBERS = [
        num.strip()
        for num in os.getenv("EMERGENCY_PHONE_NUMBERS", "+911234567890").split(",")
    ]
    EMERGENCY_EMAIL_ADDRESSES = [
        email.strip()
        for email in os.getenv("EMERGENCY_EMAIL_ADDRESSES", "emergency@example.com").split(",")
    ]

    # --- Email (SMTP) ---
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "accident-alert@example.com")

    # --- Heart Rate Thresholds ---
    HR_NORMAL_MIN = 60
    HR_NORMAL_MAX = 100
    HR_WARNING_LOW = 50
    HR_WARNING_HIGH = 120
    HR_CRITICAL_LOW = 40
    HR_CRITICAL_HIGH = 150
    HR_EMERGENCY_HIGH = 180
    HR_SUDDEN_CHANGE_BPM = 30
    HR_SUDDEN_CHANGE_WINDOW_SEC = 5
    HR_NO_PULSE_TIMEOUT_SEC = 10

    # --- SpO2 Thresholds ---
    SPO2_NORMAL_MIN = 95
    SPO2_WARNING_MIN = 90
    SPO2_CRITICAL_MIN = 80
    SPO2_EMERGENCY_MIN = 70

    # --- Accelerometer Thresholds (g) ---
    ACCEL_HARSH_BRAKE_G = 0.6
    ACCEL_IMPACT_G = 2.5
    ACCEL_SEVERE_CRASH_G = 4.0
    ACCEL_ROLLOVER_Z_G = -0.5

    # --- Gyroscope Thresholds (degrees/sec) ---
    GYRO_SUDDEN_SPIN_DPS = 120
    GYRO_HEAD_TILT_DPS = 15
    GYRO_HEAD_TILT_DURATION_SEC = 3

    # --- Face Detection ---
    DROWSINESS_SCORE_WARNING = 0.5
    DROWSINESS_SCORE_CRITICAL = 0.7
    DROWSINESS_SCORE_EMERGENCY = 0.85
    EYE_CLOSURE_DURATION_SEC = 2.0
    YAWN_FREQUENCY_PER_MIN = 3

    # --- Alert Escalation ---
    WARNING_TO_CRITICAL_SEC = 15
    CRITICAL_TO_EMERGENCY_SEC = 10
    ALERT_COOLDOWN_SEC = 60

    # --- ESP32 Command Settings ---
    MOTOR_STOP_ON_EMERGENCY = True
    BUZZER_ON_WARNING = True
    LED_BLINK_ON_ALERT = True

    # --- Data Retention ---
    SENSOR_DATA_RETENTION_HOURS = 24
    ALERT_RETENTION_DAYS = 30
