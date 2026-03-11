"""
Automatic Accident Prevention System — Flask Backend

Main application with REST API for:
  - Receiving ESP32 sensor data
  - Receiving face detection results
  - Running the decision engine
  - Sending alerts to authorities
  - Serving the live monitoring dashboard
"""

import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import Config
from models import db, SensorReading, FaceDetectionResult, Alert, SystemStatus
from decision_engine import DecisionEngine
from alert_service import AlertService

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)

# Create tables on first run
with app.app_context():
    db.create_all()
    # Ensure a SystemStatus row exists
    if not SystemStatus.query.first():
        db.session.add(SystemStatus(current_alert_level="NORMAL", motor_running=True))
        db.session.commit()

# Initialize services
decision_engine = DecisionEngine()
alert_service = AlertService()

# In-memory cache of the latest data for the dashboard
latest_data = {
    "sensor": None,
    "face": None,
    "evaluation": None,
    "last_update": None,
}

# ---------------------------------------------------------------------------
# API Routes — Sensor Data
# ---------------------------------------------------------------------------


@app.route("/api/sensor-data", methods=["POST"])
def receive_sensor_data():
    """
    Receive sensor data from ESP32.

    Expected JSON:
    {
        "heart_rate_bpm": 72.0,
        "spo2_percent": 98.0,
        "accel_x": 0.05, "accel_y": 0.08, "accel_z": -0.98,
        "gyro_x": 2.1, "gyro_y": 1.5, "gyro_z": 3.2,
        "latitude": 18.5204, "longitude": 73.8567,
        "speed_kmh": 45.0, "gps_fix": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # Save to database
        reading = SensorReading(
            heart_rate_bpm=data.get("heart_rate_bpm"),
            spo2_percent=data.get("spo2_percent"),
            accel_x=data.get("accel_x"),
            accel_y=data.get("accel_y"),
            accel_z=data.get("accel_z"),
            gyro_x=data.get("gyro_x"),
            gyro_y=data.get("gyro_y"),
            gyro_z=data.get("gyro_z"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            speed_kmh=data.get("speed_kmh"),
            gps_fix=data.get("gps_fix", False),
        )

        # Run decision engine on sensor data
        sensor_eval = decision_engine.evaluate_sensor_data(data)

        # Combine with latest face detection (if available)
        face_eval = None
        if latest_data["face"]:
            face_eval = decision_engine.evaluate_face_detection(latest_data["face"])

        combined_eval = decision_engine.combine_evaluations(sensor_eval, face_eval)
        reading.alert_level = combined_eval["alert_level"]

        db.session.add(reading)
        db.session.commit()

        # Update cached data
        latest_data["sensor"] = data
        latest_data["evaluation"] = combined_eval
        latest_data["last_update"] = datetime.utcnow().isoformat()

        # Update system status
        status = decision_engine.update_system_status(combined_eval)

        # Handle alerts
        response_data = {
            "status": "ok",
            "alert_level": combined_eval["alert_level"],
            "reasons": combined_eval["reasons"],
            "actions": combined_eval["actions"],
            "command": status.pending_command,
        }

        # If EMERGENCY — notify authorities
        if combined_eval["alert_level"] in ("CRITICAL", "EMERGENCY"):
            alert_record = decision_engine.create_alert_record(combined_eval, data)

            if combined_eval["alert_level"] == "EMERGENCY":
                alert_type = alert_record.alert_type
                if decision_engine.should_notify_authorities(
                    combined_eval["alert_level"], alert_type
                ):
                    notification = alert_service.notify_authorities(
                        alert_level=combined_eval["alert_level"],
                        reasons=combined_eval["reasons"],
                        latitude=data.get("latitude"),
                        longitude=data.get("longitude"),
                        heart_rate=data.get("heart_rate_bpm"),
                        spo2=data.get("spo2_percent"),
                        sensor_data=data,
                    )
                    alert_record.sms_sent = notification["sms"]["success"]
                    alert_record.email_sent = notification["email"]["success"]
                    alert_record.authorities_notified = notification["authorities_notified"]
                    db.session.commit()

                    response_data["notification"] = notification
                    logger.critical(f"EMERGENCY — Authorities notified: {notification}")

        # Clear pending command after ESP32 picks it up
        if status.pending_command:
            status.pending_command = None
            db.session.commit()

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error processing sensor data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API Routes — Face Detection Integration
# ---------------------------------------------------------------------------


@app.route("/api/face-detection", methods=["POST"])
def receive_face_detection():
    """
    Receive face detection results from the face detection module.

    Expected JSON:
    {
        "drowsiness_score": 0.3,
        "eyes_closed": false,
        "eye_closure_duration_sec": 0.0,
        "yawn_detected": false,
        "yawn_count_last_min": 1,
        "head_pose_pitch": 5.0,
        "head_pose_yaw": -2.0,
        "face_detected": true,
        "confidence": 0.95
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # Save to database
        result = FaceDetectionResult(
            drowsiness_score=data.get("drowsiness_score", 0.0),
            eyes_closed=data.get("eyes_closed", False),
            eye_closure_duration_sec=data.get("eye_closure_duration_sec", 0.0),
            yawn_detected=data.get("yawn_detected", False),
            yawn_count_last_min=data.get("yawn_count_last_min", 0),
            head_pose_pitch=data.get("head_pose_pitch"),
            head_pose_yaw=data.get("head_pose_yaw"),
            face_detected=data.get("face_detected", True),
            confidence=data.get("confidence", 0.0),
        )
        db.session.add(result)
        db.session.commit()

        # Cache for combination with sensor data
        latest_data["face"] = data

        # Evaluate face detection independently
        face_eval = decision_engine.evaluate_face_detection(data)

        # Update system status
        status = SystemStatus.query.first()
        if status:
            status.face_detection_active = True
            status.last_face_detection_timestamp = datetime.utcnow()
            db.session.commit()

        return jsonify({
            "status": "ok",
            "alert_level": face_eval["alert_level"],
            "drowsiness_status": face_eval["drowsiness_status"],
            "reasons": face_eval["reasons"],
        }), 200

    except Exception as e:
        logger.error(f"Error processing face detection: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API Routes — System Status & History
# ---------------------------------------------------------------------------


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get current system status and latest readings."""
    status = SystemStatus.query.first()
    return jsonify({
        "system_status": status.to_dict() if status else None,
        "latest_sensor": latest_data["sensor"],
        "latest_face": latest_data["face"],
        "latest_evaluation": latest_data["evaluation"],
        "last_update": latest_data["last_update"],
    }), 200


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get alert history. Optional query params: limit, level."""
    limit = request.args.get("limit", 50, type=int)
    level = request.args.get("level", None)

    query = Alert.query.order_by(Alert.timestamp.desc())
    if level:
        query = query.filter(Alert.alert_level == level.upper())

    alerts = query.limit(limit).all()
    return jsonify({
        "alerts": [a.to_dict() for a in alerts],
        "total": Alert.query.count(),
    }), 200


@app.route("/api/sensor-history", methods=["GET"])
def get_sensor_history():
    """Get recent sensor readings for charts. Optional query param: limit."""
    limit = request.args.get("limit", 100, type=int)
    readings = (
        SensorReading.query
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    # Reverse so oldest is first (for chart display)
    readings.reverse()
    return jsonify({
        "readings": [r.to_dict() for r in readings],
    }), 200


@app.route("/api/emergency-stop", methods=["POST"])
def emergency_stop():
    """Manual emergency stop trigger."""
    status = SystemStatus.query.first()
    if status:
        status.motor_running = False
        status.pending_command = "STOP_MOTOR"
        status.buzzer_active = True
        status.current_alert_level = "EMERGENCY"
        db.session.commit()

    # Create alert record
    alert = Alert(
        alert_level="EMERGENCY",
        alert_type="manual_stop",
        message="Manual emergency stop triggered",
        motor_stopped=True,
        buzzer_activated=True,
        latitude=(
            latest_data["sensor"].get("latitude")
            if latest_data["sensor"]
            else None
        ),
        longitude=(
            latest_data["sensor"].get("longitude")
            if latest_data["sensor"]
            else None
        ),
    )
    db.session.add(alert)
    db.session.commit()

    # Notify authorities
    notification = alert_service.notify_authorities(
        alert_level="EMERGENCY",
        reasons=["Manual emergency stop triggered by operator"],
        latitude=alert.latitude,
        longitude=alert.longitude,
        heart_rate=(
            latest_data["sensor"].get("heart_rate_bpm")
            if latest_data["sensor"]
            else None
        ),
        spo2=(
            latest_data["sensor"].get("spo2_percent")
            if latest_data["sensor"]
            else None
        ),
        sensor_data=latest_data["sensor"],
    )

    alert.sms_sent = notification["sms"]["success"]
    alert.email_sent = notification["email"]["success"]
    alert.authorities_notified = notification["authorities_notified"]
    db.session.commit()

    logger.critical("MANUAL EMERGENCY STOP TRIGGERED")

    return jsonify({
        "status": "emergency_stop_activated",
        "notification": notification,
    }), 200


@app.route("/api/reset", methods=["POST"])
def reset_system():
    """Reset system to NORMAL state (after emergency is resolved)."""
    status = SystemStatus.query.first()
    if status:
        status.current_alert_level = "NORMAL"
        status.motor_running = True
        status.buzzer_active = False
        status.led_active = False
        status.pending_command = "RESET"
        db.session.commit()

    logger.info("System reset to NORMAL")

    return jsonify({"status": "system_reset", "alert_level": "NORMAL"}), 200


@app.route("/api/esp32-command", methods=["GET"])
def get_esp32_command():
    """
    Endpoint for ESP32 to poll for pending commands.
    Returns and clears the pending command.
    """
    status = SystemStatus.query.first()
    command = None
    if status and status.pending_command:
        command = status.pending_command
        status.pending_command = None
        status.esp32_connected = True
        db.session.commit()
    elif status:
        status.esp32_connected = True
        db.session.commit()

    return jsonify({"command": command}), 200


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@app.route("/dashboard")
@app.route("/")
def dashboard():
    """Serve the live monitoring dashboard."""
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Accident Prevention System — Backend Starting")
    logger.info("=" * 60)
    logger.info(f"  Dashboard: http://localhost:5000/dashboard")
    logger.info(f"  API Docs:  POST /api/sensor-data")
    logger.info(f"             POST /api/face-detection")
    logger.info(f"             GET  /api/status")
    logger.info(f"             GET  /api/alerts")
    logger.info(f"             POST /api/emergency-stop")
    logger.info(f"             POST /api/reset")
    logger.info(f"             GET  /api/esp32-command")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
