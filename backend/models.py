from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class SensorReading(db.Model):
    """Stores each sensor data reading from the ESP32."""

    __tablename__ = "sensor_readings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # MAX30102 readings
    heart_rate_bpm = db.Column(db.Float, nullable=True)
    spo2_percent = db.Column(db.Float, nullable=True)

    # MPU6050 readings
    accel_x = db.Column(db.Float, nullable=True)
    accel_y = db.Column(db.Float, nullable=True)
    accel_z = db.Column(db.Float, nullable=True)
    gyro_x = db.Column(db.Float, nullable=True)
    gyro_y = db.Column(db.Float, nullable=True)
    gyro_z = db.Column(db.Float, nullable=True)

    # GPS NEO-6M readings
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    speed_kmh = db.Column(db.Float, nullable=True)
    gps_fix = db.Column(db.Boolean, default=False)

    # Computed
    alert_level = db.Column(db.String(20), default="NORMAL")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "heart_rate_bpm": self.heart_rate_bpm,
            "spo2_percent": self.spo2_percent,
            "accel_x": self.accel_x,
            "accel_y": self.accel_y,
            "accel_z": self.accel_z,
            "gyro_x": self.gyro_x,
            "gyro_y": self.gyro_y,
            "gyro_z": self.gyro_z,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed_kmh": self.speed_kmh,
            "gps_fix": self.gps_fix,
            "alert_level": self.alert_level,
        }


class FaceDetectionResult(db.Model):
    """Stores face detection analysis results."""

    __tablename__ = "face_detection_results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    drowsiness_score = db.Column(db.Float, default=0.0)  # 0.0 = fully awake, 1.0 = asleep
    eyes_closed = db.Column(db.Boolean, default=False)
    eye_closure_duration_sec = db.Column(db.Float, default=0.0)
    yawn_detected = db.Column(db.Boolean, default=False)
    yawn_count_last_min = db.Column(db.Integer, default=0)
    head_pose_pitch = db.Column(db.Float, nullable=True)  # head tilt forward/back
    head_pose_yaw = db.Column(db.Float, nullable=True)  # head turn left/right
    face_detected = db.Column(db.Boolean, default=True)
    confidence = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "drowsiness_score": self.drowsiness_score,
            "eyes_closed": self.eyes_closed,
            "eye_closure_duration_sec": self.eye_closure_duration_sec,
            "yawn_detected": self.yawn_detected,
            "yawn_count_last_min": self.yawn_count_last_min,
            "head_pose_pitch": self.head_pose_pitch,
            "head_pose_yaw": self.head_pose_yaw,
            "face_detected": self.face_detected,
            "confidence": self.confidence,
        }


class Alert(db.Model):
    """Stores generated alerts and notifications."""

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    alert_level = db.Column(db.String(20), nullable=False)  # WARNING, CRITICAL, EMERGENCY
    alert_type = db.Column(db.String(50), nullable=False)  # heart_rate, spo2, impact, drowsiness, etc.
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string of trigger data

    # Location at time of alert
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Actions taken
    motor_stopped = db.Column(db.Boolean, default=False)
    buzzer_activated = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    authorities_notified = db.Column(db.Boolean, default=False)

    # Resolution
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(50), nullable=True)  # "system" or "manual"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "alert_level": self.alert_level,
            "alert_type": self.alert_type,
            "message": self.message,
            "details": self.details,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "motor_stopped": self.motor_stopped,
            "buzzer_activated": self.buzzer_activated,
            "sms_sent": self.sms_sent,
            "email_sent": self.email_sent,
            "authorities_notified": self.authorities_notified,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


class SystemStatus(db.Model):
    """Tracks current system state."""

    __tablename__ = "system_status"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    current_alert_level = db.Column(db.String(20), default="NORMAL")
    motor_running = db.Column(db.Boolean, default=True)
    buzzer_active = db.Column(db.Boolean, default=False)
    led_active = db.Column(db.Boolean, default=False)
    esp32_connected = db.Column(db.Boolean, default=False)
    face_detection_active = db.Column(db.Boolean, default=False)
    last_sensor_timestamp = db.Column(db.DateTime, nullable=True)
    last_face_detection_timestamp = db.Column(db.DateTime, nullable=True)

    # Pending command for ESP32 to pick up
    pending_command = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "current_alert_level": self.current_alert_level,
            "motor_running": self.motor_running,
            "buzzer_active": self.buzzer_active,
            "led_active": self.led_active,
            "esp32_connected": self.esp32_connected,
            "face_detection_active": self.face_detection_active,
            "last_sensor_timestamp": (
                self.last_sensor_timestamp.isoformat() if self.last_sensor_timestamp else None
            ),
            "last_face_detection_timestamp": (
                self.last_face_detection_timestamp.isoformat()
                if self.last_face_detection_timestamp
                else None
            ),
            "pending_command": self.pending_command,
        }
