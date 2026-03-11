"""
Alert Service — SMS (Twilio) and Email notification system.

Sends emergency alerts to configured authorities with GPS coordinates
and a Google Maps link for immediate response.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)


class AlertService:
    """Handles sending alerts via SMS and Email."""

    def __init__(self):
        self.twilio_client = None
        self._init_twilio()

    def _init_twilio(self):
        """Initialize Twilio client if credentials are provided."""
        if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    Config.TWILIO_ACCOUNT_SID,
                    Config.TWILIO_AUTH_TOKEN,
                )
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.warning("Twilio package not installed. SMS alerts disabled.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.warning("Twilio credentials not provided. SMS alerts disabled.")

    def send_emergency_sms(
        self,
        alert_level: str,
        reasons: list,
        latitude: float = None,
        longitude: float = None,
        heart_rate: float = None,
        spo2: float = None,
    ) -> dict:
        """
        Send emergency SMS to all configured emergency contacts.

        Returns dict with status and details.
        """
        results = {"success": False, "messages_sent": 0, "errors": []}

        # Build the message
        message_body = self._build_sms_message(
            alert_level, reasons, latitude, longitude, heart_rate, spo2
        )

        if not self.twilio_client:
            # Log the message even if Twilio is not configured (for testing)
            logger.warning(f"SMS not sent (Twilio not configured). Message:\n{message_body}")
            results["errors"].append("Twilio not configured")
            results["message_preview"] = message_body
            return results

        for phone_number in Config.EMERGENCY_PHONE_NUMBERS:
            try:
                message = self.twilio_client.messages.create(
                    body=message_body,
                    from_=Config.TWILIO_PHONE_NUMBER,
                    to=phone_number,
                )
                results["messages_sent"] += 1
                logger.info(f"SMS sent to {phone_number}: SID={message.sid}")
            except Exception as e:
                error_msg = f"Failed to send SMS to {phone_number}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        results["success"] = results["messages_sent"] > 0
        return results

    def send_emergency_email(
        self,
        alert_level: str,
        reasons: list,
        latitude: float = None,
        longitude: float = None,
        heart_rate: float = None,
        spo2: float = None,
        sensor_data: dict = None,
    ) -> dict:
        """Send emergency email to all configured emergency email contacts."""
        results = {"success": False, "emails_sent": 0, "errors": []}

        if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured. Email alerts disabled.")
            results["errors"].append("SMTP not configured")
            return results

        subject = f"🚨 {alert_level} ALERT — Accident Prevention System"
        html_body = self._build_email_html(
            alert_level, reasons, latitude, longitude,
            heart_rate, spo2, sensor_data,
        )

        for email_address in Config.EMERGENCY_EMAIL_ADDRESSES:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = Config.SMTP_FROM_EMAIL
                msg["To"] = email_address

                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                    server.starttls()
                    server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                    server.sendmail(Config.SMTP_FROM_EMAIL, email_address, msg.as_string())

                results["emails_sent"] += 1
                logger.info(f"Emergency email sent to {email_address}")
            except Exception as e:
                error_msg = f"Failed to send email to {email_address}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        results["success"] = results["emails_sent"] > 0
        return results

    def notify_authorities(
        self,
        alert_level: str,
        reasons: list,
        latitude: float = None,
        longitude: float = None,
        heart_rate: float = None,
        spo2: float = None,
        sensor_data: dict = None,
    ) -> dict:
        """
        Master notification method — sends both SMS and email.
        Returns combined results.
        """
        logger.critical(
            f"NOTIFYING AUTHORITIES — Level: {alert_level}, "
            f"Location: ({latitude}, {longitude}), Reasons: {reasons}"
        )

        sms_result = self.send_emergency_sms(
            alert_level, reasons, latitude, longitude, heart_rate, spo2
        )
        email_result = self.send_emergency_email(
            alert_level, reasons, latitude, longitude,
            heart_rate, spo2, sensor_data,
        )

        return {
            "sms": sms_result,
            "email": email_result,
            "authorities_notified": sms_result["success"] or email_result["success"],
        }

    # -------------------------------------------------------------------------
    # Message builders
    # -------------------------------------------------------------------------

    def _build_sms_message(
        self, alert_level, reasons, latitude, longitude, heart_rate, spo2
    ) -> str:
        """Build a concise SMS message with critical info."""
        lines = [
            f"🚨 {alert_level} — ACCIDENT PREVENTION SYSTEM",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if latitude and longitude:
            lines.append(f"📍 Location: {latitude:.6f}, {longitude:.6f}")
            lines.append(
                f"🗺️ Map: https://maps.google.com/maps?q={latitude},{longitude}"
            )

        if heart_rate:
            lines.append(f"❤️ Heart Rate: {heart_rate:.0f} BPM")
        if spo2:
            lines.append(f"🫁 SpO2: {spo2:.0f}%")

        if reasons:
            lines.append(f"⚠️ Alert: {reasons[0]}")
            if len(reasons) > 1:
                lines.append(f"+ {len(reasons) - 1} more warnings")

        lines.append("IMMEDIATE ASSISTANCE REQUIRED")

        return "\n".join(lines)

    def _build_email_html(
        self, alert_level, reasons, latitude, longitude,
        heart_rate, spo2, sensor_data,
    ) -> str:
        """Build a detailed HTML email for emergency notification."""
        map_link = ""
        if latitude and longitude:
            map_link = f"https://maps.google.com/maps?q={latitude},{longitude}"

        reasons_html = ""
        for reason in reasons:
            reasons_html += f"<li style='padding:4px 0;'>{reason}</li>"

        sensor_html = ""
        if sensor_data:
            sensor_html = f"""
            <table style="width:100%;border-collapse:collapse;margin:10px 0;">
                <tr style="background:#f8d7da;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Heart Rate</td>
                    <td style="padding:8px;border:1px solid #ddd;">{sensor_data.get('heart_rate_bpm', 'N/A')} BPM</td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">SpO2</td>
                    <td style="padding:8px;border:1px solid #ddd;">{sensor_data.get('spo2_percent', 'N/A')}%</td>
                </tr>
                <tr style="background:#f8d7da;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Speed</td>
                    <td style="padding:8px;border:1px solid #ddd;">{sensor_data.get('speed_kmh', 'N/A')} km/h</td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Acceleration</td>
                    <td style="padding:8px;border:1px solid #ddd;">
                        X:{sensor_data.get('accel_x', 'N/A')}g
                        Y:{sensor_data.get('accel_y', 'N/A')}g
                        Z:{sensor_data.get('accel_z', 'N/A')}g
                    </td>
                </tr>
            </table>
            """

        return f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#dc3545;color:white;padding:20px;text-align:center;border-radius:8px 8px 0 0;">
                <h1 style="margin:0;">🚨 {alert_level} ALERT</h1>
                <p style="margin:5px 0 0;">Automatic Accident Prevention System</p>
            </div>

            <div style="padding:20px;background:#fff;border:1px solid #ddd;">
                <p style="font-size:16px;color:#333;">
                    <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>

                {'<p style="font-size:16px;"><strong>📍 Location:</strong> '
                 + f'<a href="{map_link}">{latitude:.6f}, {longitude:.6f}</a></p>'
                 if latitude and longitude else '<p>📍 Location: Not available</p>'}

                <h3 style="color:#dc3545;border-bottom:2px solid #dc3545;padding-bottom:5px;">
                    Alert Details
                </h3>
                <ul style="color:#333;line-height:1.8;">
                    {reasons_html}
                </ul>

                {f'<h3 style="color:#333;">Sensor Readings</h3>{sensor_html}' if sensor_html else ''}

                {'<div style="text-align:center;margin:20px 0;">'
                 + f'<a href="{map_link}" style="background:#dc3545;color:white;'
                 + 'padding:12px 30px;text-decoration:none;border-radius:5px;'
                 + 'font-size:16px;font-weight:bold;">📍 View Location on Map</a>'
                 + '</div>' if map_link else ''}
            </div>

            <div style="background:#f8f9fa;padding:15px;text-align:center;
                        border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;">
                <p style="color:#666;font-size:12px;margin:0;">
                    This is an automated alert from the Accident Prevention System.
                    Please respond immediately if you receive this message.
                </p>
            </div>
        </body>
        </html>
        """
