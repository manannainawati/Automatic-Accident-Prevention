"""
Decision Engine — Core alert logic for the Accident Prevention System.

Evaluates sensor data + face detection results to determine alert levels:
  NORMAL → WARNING → CRITICAL → EMERGENCY

On EMERGENCY:
  - Motor is stopped
  - Authorities are notified via SMS/email with GPS coordinates
"""

import json
import math
from datetime import datetime, timedelta
from config import Config
from models import db, SensorReading, FaceDetectionResult, Alert, SystemStatus


class DecisionEngine:
    """Processes sensor data and determines system alert level."""

    def __init__(self):
        self.recent_heart_rates = []  # (timestamp, bpm) tuples
        self.last_alert_time = {}     # alert_type -> last alert timestamp
        self.consecutive_warnings = 0
        self.warning_start_time = None
        self.critical_start_time = None

    def evaluate_sensor_data(self, sensor_data: dict) -> dict:
        """
        Main evaluation method. Takes a sensor reading dict and returns
        an alert result with level, reasons, and recommended actions.
        """
        results = {
            "alert_level": "NORMAL",
            "reasons": [],
            "actions": [],
            "heart_rate_status": "OK",
            "spo2_status": "OK",
            "motion_status": "OK",
            "drowsiness_status": "OK",
        }

        # --- Evaluate Heart Rate ---
        hr_result = self._evaluate_heart_rate(sensor_data.get("heart_rate_bpm"))
        results["heart_rate_status"] = hr_result["status"]
        if hr_result["level"] != "NORMAL":
            results["reasons"].append(hr_result["reason"])
            results["alert_level"] = self._escalate_level(
                results["alert_level"], hr_result["level"]
            )

        # --- Evaluate SpO2 ---
        spo2_result = self._evaluate_spo2(sensor_data.get("spo2_percent"))
        results["spo2_status"] = spo2_result["status"]
        if spo2_result["level"] != "NORMAL":
            results["reasons"].append(spo2_result["reason"])
            results["alert_level"] = self._escalate_level(
                results["alert_level"], spo2_result["level"]
            )

        # --- Evaluate Motion (MPU6050) ---
        motion_result = self._evaluate_motion(
            sensor_data.get("accel_x", 0),
            sensor_data.get("accel_y", 0),
            sensor_data.get("accel_z", -1),
            sensor_data.get("gyro_x", 0),
            sensor_data.get("gyro_y", 0),
            sensor_data.get("gyro_z", 0),
        )
        results["motion_status"] = motion_result["status"]
        if motion_result["level"] != "NORMAL":
            results["reasons"].append(motion_result["reason"])
            results["alert_level"] = self._escalate_level(
                results["alert_level"], motion_result["level"]
            )

        # --- Evaluate Heart Rate Variability (sudden changes) ---
        hrv_result = self._evaluate_heart_rate_variability(
            sensor_data.get("heart_rate_bpm")
        )
        if hrv_result and hrv_result["level"] != "NORMAL":
            results["reasons"].append(hrv_result["reason"])
            results["alert_level"] = self._escalate_level(
                results["alert_level"], hrv_result["level"]
            )

        # --- Determine actions based on alert level ---
        results["actions"] = self._determine_actions(results["alert_level"])

        # --- Track escalation timing ---
        self._track_escalation(results["alert_level"])

        return results

    def evaluate_face_detection(self, face_data: dict) -> dict:
        """Evaluate face detection results for drowsiness."""
        results = {
            "alert_level": "NORMAL",
            "reasons": [],
            "drowsiness_status": "AWAKE",
        }

        drowsiness_score = face_data.get("drowsiness_score", 0.0)
        eyes_closed = face_data.get("eyes_closed", False)
        eye_closure_duration = face_data.get("eye_closure_duration_sec", 0.0)
        yawn_count = face_data.get("yawn_count_last_min", 0)
        face_detected = face_data.get("face_detected", True)

        # No face detected — driver may have left seat or camera issue
        if not face_detected:
            results["alert_level"] = "WARNING"
            results["reasons"].append("Driver face not detected — possible absence or camera obstruction")
            results["drowsiness_status"] = "UNKNOWN"
            return results

        # Drowsiness score evaluation
        if drowsiness_score >= Config.DROWSINESS_SCORE_EMERGENCY:
            results["alert_level"] = "EMERGENCY"
            results["reasons"].append(
                f"Severe drowsiness detected (score: {drowsiness_score:.2f})"
            )
            results["drowsiness_status"] = "ASLEEP"
        elif drowsiness_score >= Config.DROWSINESS_SCORE_CRITICAL:
            results["alert_level"] = "CRITICAL"
            results["reasons"].append(
                f"High drowsiness detected (score: {drowsiness_score:.2f})"
            )
            results["drowsiness_status"] = "VERY_DROWSY"
        elif drowsiness_score >= Config.DROWSINESS_SCORE_WARNING:
            results["alert_level"] = "WARNING"
            results["reasons"].append(
                f"Drowsiness indicators detected (score: {drowsiness_score:.2f})"
            )
            results["drowsiness_status"] = "DROWSY"

        # Prolonged eye closure
        if eyes_closed and eye_closure_duration >= Config.EYE_CLOSURE_DURATION_SEC:
            new_level = "EMERGENCY" if eye_closure_duration >= 4.0 else "CRITICAL"
            results["alert_level"] = self._escalate_level(
                results["alert_level"], new_level
            )
            results["reasons"].append(
                f"Eyes closed for {eye_closure_duration:.1f} seconds"
            )

        # Frequent yawning
        if yawn_count >= Config.YAWN_FREQUENCY_PER_MIN:
            results["alert_level"] = self._escalate_level(
                results["alert_level"], "WARNING"
            )
            results["reasons"].append(
                f"Frequent yawning detected ({yawn_count} in last minute)"
            )

        return results

    def combine_evaluations(self, sensor_result: dict, face_result: dict = None) -> dict:
        """
        Combine sensor and face detection evaluations to produce final alert level.
        Multiple warning signs simultaneously increase severity.
        """
        combined = {
            "alert_level": sensor_result["alert_level"],
            "reasons": list(sensor_result.get("reasons", [])),
            "actions": [],
            "heart_rate_status": sensor_result.get("heart_rate_status", "OK"),
            "spo2_status": sensor_result.get("spo2_status", "OK"),
            "motion_status": sensor_result.get("motion_status", "OK"),
            "drowsiness_status": sensor_result.get("drowsiness_status", "OK"),
        }

        if face_result:
            combined["drowsiness_status"] = face_result.get("drowsiness_status", "OK")
            combined["reasons"].extend(face_result.get("reasons", []))
            combined["alert_level"] = self._escalate_level(
                combined["alert_level"], face_result["alert_level"]
            )

        # --- Multi-factor escalation ---
        # If multiple WARNING-level issues exist simultaneously, escalate to CRITICAL
        warning_count = sum(
            1
            for status in [
                combined["heart_rate_status"],
                combined["spo2_status"],
                combined["motion_status"],
                combined["drowsiness_status"],
            ]
            if status not in ("OK", "AWAKE", "NORMAL")
        )

        if warning_count >= 2 and combined["alert_level"] == "WARNING":
            combined["alert_level"] = "CRITICAL"
            combined["reasons"].append("Multiple warning indicators active — escalating to CRITICAL")

        if warning_count >= 3 and combined["alert_level"] == "CRITICAL":
            combined["alert_level"] = "EMERGENCY"
            combined["reasons"].append("Multiple systems in alert — escalating to EMERGENCY")

        combined["actions"] = self._determine_actions(combined["alert_level"])
        return combined

    def create_alert_record(self, evaluation: dict, sensor_data: dict) -> Alert:
        """Create and save an Alert record to the database."""
        alert = Alert(
            alert_level=evaluation["alert_level"],
            alert_type=self._determine_alert_type(evaluation),
            message=" | ".join(evaluation.get("reasons", ["Unknown alert"])),
            details=json.dumps(
                {
                    "sensor_data": sensor_data,
                    "evaluation": {
                        k: v
                        for k, v in evaluation.items()
                        if k not in ("actions",)
                    },
                }
            ),
            latitude=sensor_data.get("latitude"),
            longitude=sensor_data.get("longitude"),
            motor_stopped="STOP_MOTOR" in evaluation.get("actions", []),
            buzzer_activated="ACTIVATE_BUZZER" in evaluation.get("actions", []),
        )
        db.session.add(alert)
        db.session.commit()
        return alert

    def update_system_status(self, evaluation: dict) -> SystemStatus:
        """Update the system status record."""
        status = SystemStatus.query.first()
        if not status:
            status = SystemStatus()
            db.session.add(status)

        status.current_alert_level = evaluation["alert_level"]
        status.updated_at = datetime.utcnow()

        if "STOP_MOTOR" in evaluation.get("actions", []):
            status.motor_running = False
            status.pending_command = "STOP_MOTOR"
        if "ACTIVATE_BUZZER" in evaluation.get("actions", []):
            status.buzzer_active = True
        if "ACTIVATE_LED" in evaluation.get("actions", []):
            status.led_active = True

        status.last_sensor_timestamp = datetime.utcnow()
        db.session.commit()
        return status

    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------

    def _evaluate_heart_rate(self, bpm) -> dict:
        if bpm is None or bpm == 0:
            return {
                "level": "WARNING",
                "status": "NO_READING",
                "reason": "Heart rate sensor not reading — check sensor placement",
            }

        if bpm >= Config.HR_EMERGENCY_HIGH:
            return {
                "level": "EMERGENCY",
                "status": "EMERGENCY_HIGH",
                "reason": f"Heart rate extremely high: {bpm} BPM — possible cardiac emergency",
            }
        elif bpm >= Config.HR_CRITICAL_HIGH:
            return {
                "level": "CRITICAL",
                "status": "CRITICAL_HIGH",
                "reason": f"Heart rate dangerously high: {bpm} BPM",
            }
        elif bpm >= Config.HR_WARNING_HIGH:
            return {
                "level": "WARNING",
                "status": "HIGH",
                "reason": f"Heart rate elevated: {bpm} BPM",
            }
        elif bpm <= Config.HR_CRITICAL_LOW:
            return {
                "level": "CRITICAL",
                "status": "CRITICAL_LOW",
                "reason": f"Heart rate dangerously low: {bpm} BPM — possible bradycardia",
            }
        elif bpm <= Config.HR_WARNING_LOW:
            return {
                "level": "WARNING",
                "status": "LOW",
                "reason": f"Heart rate low: {bpm} BPM",
            }
        else:
            return {"level": "NORMAL", "status": "OK", "reason": ""}

    def _evaluate_spo2(self, spo2) -> dict:
        if spo2 is None or spo2 == 0:
            return {
                "level": "WARNING",
                "status": "NO_READING",
                "reason": "SpO2 sensor not reading",
            }

        if spo2 < Config.SPO2_EMERGENCY_MIN:
            return {
                "level": "EMERGENCY",
                "status": "EMERGENCY",
                "reason": f"SpO2 critically low: {spo2}% — severe hypoxemia",
            }
        elif spo2 < Config.SPO2_CRITICAL_MIN:
            return {
                "level": "CRITICAL",
                "status": "CRITICAL",
                "reason": f"SpO2 dangerously low: {spo2}% — medical attention needed",
            }
        elif spo2 < Config.SPO2_WARNING_MIN:
            return {
                "level": "WARNING",
                "status": "LOW",
                "reason": f"SpO2 below normal: {spo2}%",
            }
        elif spo2 < Config.SPO2_NORMAL_MIN:
            return {
                "level": "WARNING",
                "status": "SLIGHTLY_LOW",
                "reason": f"SpO2 slightly low: {spo2}%",
            }
        else:
            return {"level": "NORMAL", "status": "OK", "reason": ""}

    def _evaluate_motion(self, ax, ay, az, gx, gy, gz) -> dict:
        # Calculate total acceleration magnitude
        accel_magnitude = math.sqrt(ax**2 + ay**2 + az**2)
        # For impact, we care about deviation from 1g (gravity)
        accel_deviation = abs(accel_magnitude - 1.0)

        # Calculate total gyro magnitude
        gyro_magnitude = math.sqrt(gx**2 + gy**2 + gz**2)

        # Check for severe crash
        if accel_deviation >= Config.ACCEL_SEVERE_CRASH_G:
            return {
                "level": "EMERGENCY",
                "status": "SEVERE_CRASH",
                "reason": f"Severe crash detected — acceleration: {accel_deviation:.2f}g",
            }

        # Check for impact
        if accel_deviation >= Config.ACCEL_IMPACT_G:
            return {
                "level": "CRITICAL",
                "status": "IMPACT",
                "reason": f"Impact detected — acceleration: {accel_deviation:.2f}g",
            }

        # Check for rollover (z-axis significantly negative)
        if az >= Config.ACCEL_ROLLOVER_Z_G and az < 0:
            return {
                "level": "EMERGENCY",
                "status": "ROLLOVER",
                "reason": f"Possible rollover detected — Z-axis: {az:.2f}g",
            }

        # Check for sudden spin (loss of control)
        if gyro_magnitude >= Config.GYRO_SUDDEN_SPIN_DPS:
            return {
                "level": "CRITICAL",
                "status": "SPIN",
                "reason": f"Rapid spinning detected — gyro: {gyro_magnitude:.1f}°/s",
            }

        # Check for harsh braking
        if abs(ay) >= Config.ACCEL_HARSH_BRAKE_G:
            return {
                "level": "WARNING",
                "status": "HARSH_BRAKE",
                "reason": f"Harsh braking detected — deceleration: {abs(ay):.2f}g",
            }

        return {"level": "NORMAL", "status": "OK", "reason": ""}

    def _evaluate_heart_rate_variability(self, bpm) -> dict:
        if bpm is None or bpm == 0:
            return None

        now = datetime.utcnow()
        self.recent_heart_rates.append((now, bpm))

        # Keep only recent readings within the window
        cutoff = now - timedelta(seconds=Config.HR_SUDDEN_CHANGE_WINDOW_SEC)
        self.recent_heart_rates = [
            (t, hr) for t, hr in self.recent_heart_rates if t >= cutoff
        ]

        if len(self.recent_heart_rates) >= 2:
            oldest_hr = self.recent_heart_rates[0][1]
            newest_hr = self.recent_heart_rates[-1][1]
            change = abs(newest_hr - oldest_hr)

            if change >= Config.HR_SUDDEN_CHANGE_BPM:
                return {
                    "level": "CRITICAL",
                    "status": "SUDDEN_CHANGE",
                    "reason": (
                        f"Sudden heart rate change: {change:.0f} BPM "
                        f"in {Config.HR_SUDDEN_CHANGE_WINDOW_SEC}s "
                        f"({oldest_hr:.0f} → {newest_hr:.0f})"
                    ),
                }

        return {"level": "NORMAL", "status": "OK", "reason": ""}

    def _escalate_level(self, current: str, new: str) -> str:
        """Return the higher of two alert levels."""
        levels = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2, "EMERGENCY": 3}
        if levels.get(new, 0) > levels.get(current, 0):
            return new
        return current

    def _determine_actions(self, alert_level: str) -> list:
        actions = []
        if alert_level == "WARNING":
            if Config.BUZZER_ON_WARNING:
                actions.append("ACTIVATE_BUZZER")
            if Config.LED_BLINK_ON_ALERT:
                actions.append("ACTIVATE_LED")
        elif alert_level == "CRITICAL":
            actions.append("ACTIVATE_BUZZER")
            actions.append("ACTIVATE_LED")
            actions.append("SEND_WARNING_SMS")
        elif alert_level == "EMERGENCY":
            actions.append("ACTIVATE_BUZZER")
            actions.append("ACTIVATE_LED")
            if Config.MOTOR_STOP_ON_EMERGENCY:
                actions.append("STOP_MOTOR")
            actions.append("NOTIFY_AUTHORITIES")
            actions.append("SEND_EMERGENCY_SMS")
            actions.append("SEND_EMERGENCY_EMAIL")
        return actions

    def _determine_alert_type(self, evaluation: dict) -> str:
        """Determine the primary alert type from evaluation results."""
        reasons_text = " ".join(evaluation.get("reasons", []))
        if "crash" in reasons_text.lower() or "impact" in reasons_text.lower():
            return "crash_detected"
        elif "heart" in reasons_text.lower() or "cardiac" in reasons_text.lower():
            return "heart_anomaly"
        elif "spo2" in reasons_text.lower() or "oxygen" in reasons_text.lower():
            return "low_oxygen"
        elif "drowsi" in reasons_text.lower() or "eyes" in reasons_text.lower():
            return "drowsiness"
        elif "rollover" in reasons_text.lower():
            return "rollover"
        elif "spin" in reasons_text.lower():
            return "loss_of_control"
        else:
            return "general_alert"

    def _track_escalation(self, alert_level: str):
        """Track time spent at each alert level for escalation logic."""
        now = datetime.utcnow()

        if alert_level == "WARNING":
            if self.warning_start_time is None:
                self.warning_start_time = now
            self.consecutive_warnings += 1
            self.critical_start_time = None
        elif alert_level == "CRITICAL":
            if self.critical_start_time is None:
                self.critical_start_time = now
            self.warning_start_time = None
        elif alert_level == "NORMAL":
            self.warning_start_time = None
            self.critical_start_time = None
            self.consecutive_warnings = 0

    def should_notify_authorities(self, alert_level: str, alert_type: str) -> bool:
        """Check if authorities should be notified (with cooldown)."""
        if alert_level != "EMERGENCY":
            return False

        now = datetime.utcnow()
        last_alert = self.last_alert_time.get(alert_type)

        if last_alert is None:
            self.last_alert_time[alert_type] = now
            return True

        elapsed = (now - last_alert).total_seconds()
        if elapsed >= Config.ALERT_COOLDOWN_SEC:
            self.last_alert_time[alert_type] = now
            return True

        return False
