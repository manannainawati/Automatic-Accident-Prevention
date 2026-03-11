/*
 * ============================================================
 * Automatic Accident Prevention System — ESP32 Firmware
 * ============================================================
 *
 * Hardware:
 *   - ESP32 DevKit V1
 *   - MAX30102  (Heart Rate + SpO2, I2C)
 *   - MPU6050   (Accelerometer + Gyroscope, I2C)
 *   - GPS NEO-6M (UART)
 *   - Buzzer    (Digital output)
 *   - LED       (Digital output)
 *   - 100 RPM Gear Motor (Digital output via motor driver)
 *
 * Pin Connections:
 *   MAX30102:  SDA -> GPIO 21,  SCL -> GPIO 22  (default I2C)
 *   MPU6050:   SDA -> GPIO 21,  SCL -> GPIO 22  (shared I2C bus)
 *   GPS:       TX  -> GPIO 16 (ESP32 RX2),  RX -> GPIO 17 (ESP32 TX2)
 *   Buzzer:    Signal -> GPIO 25
 *   LED:       Anode  -> GPIO 26 (with 220Ω resistor)
 *   Motor:     IN1 -> GPIO 27 (via L298N or motor driver)
 *
 * Libraries Required (install via Arduino Library Manager):
 *   - MAX30105 by SparkFun
 *   - Adafruit MPU6050
 *   - TinyGPSPlus by Mikal Hart
 *   - WiFi (built-in)
 *   - HTTPClient (built-in)
 *   - ArduinoJson by Benoit Blanchon
 *   - Wire (built-in, for I2C)
 *
 * ============================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- MAX30102 ---
#include "MAX30105.h"
#include "heartRate.h"

// --- MPU6050 ---
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// --- GPS ---
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

// ============================================================
//  CONFIGURATION — EDIT THESE VALUES
// ============================================================

// WiFi credentials
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend server (use your computer's local IP when on same WiFi)
const char* SERVER_URL      = "http://192.168.1.100:5000";
const char* SENSOR_ENDPOINT = "/api/sensor-data";
const char* CMD_ENDPOINT    = "/api/esp32-command";

// Data send interval (milliseconds)
const unsigned long SEND_INTERVAL = 2000;

// ============================================================
//  PIN DEFINITIONS
// ============================================================

#define BUZZER_PIN   25
#define LED_PIN      26
#define MOTOR_PIN    27

// GPS on Serial2
#define GPS_RX_PIN   16
#define GPS_TX_PIN   17
#define GPS_BAUD     9600

// ============================================================
//  HEART RATE THRESHOLDS (local emergency detection)
// ============================================================

#define HR_WARNING_LOW    50
#define HR_WARNING_HIGH   120
#define HR_CRITICAL_LOW   40
#define HR_CRITICAL_HIGH  150
#define HR_EMERGENCY      180
#define SPO2_WARNING      90
#define SPO2_CRITICAL     80

// ============================================================
//  GLOBAL OBJECTS
// ============================================================

MAX30105 particleSensor;
Adafruit_MPU6050 mpu;
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

// ============================================================
//  STATE VARIABLES
// ============================================================

unsigned long lastSendTime = 0;
unsigned long lastCmdPollTime = 0;
const unsigned long CMD_POLL_INTERVAL = 3000;

bool motorRunning = true;
bool buzzerActive = false;
bool ledActive = false;
bool wifiConnected = false;

// Heart rate calculation
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0;
int beatAvg = 0;

// Sensor data
float heartRate = 0;
float spO2 = 0;
float accelX = 0, accelY = 0, accelZ = 0;
float gyroX = 0, gyroY = 0, gyroZ = 0;
double latitude = 0, longitude = 0;
float speedKmh = 0;
bool gpsFix = false;

// ============================================================
//  SETUP
// ============================================================

void setup() {
    Serial.begin(115200);
    Serial.println("\n============================================");
    Serial.println("  Accident Prevention System — Starting");
    Serial.println("============================================\n");

    // --- Pin setup ---
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    pinMode(MOTOR_PIN, OUTPUT);

    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(MOTOR_PIN, HIGH);  // Motor ON by default
    motorRunning = true;

    // --- I2C ---
    Wire.begin();

    // --- Initialize MAX30102 ---
    Serial.print("[MAX30102] Initializing... ");
    if (particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("OK");
        particleSensor.setup();
        particleSensor.setPulseAmplitudeRed(0x0A);
        particleSensor.setPulseAmplitudeGreen(0);
    } else {
        Serial.println("FAILED! Check wiring.");
    }

    // --- Initialize MPU6050 ---
    Serial.print("[MPU6050]  Initializing... ");
    if (mpu.begin()) {
        Serial.println("OK");
        mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
        mpu.setGyroRange(MPU6050_RANGE_500_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    } else {
        Serial.println("FAILED! Check wiring.");
    }

    // --- Initialize GPS ---
    Serial.print("[GPS]      Initializing... ");
    gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
    Serial.println("OK (waiting for fix)");

    // --- Connect WiFi ---
    connectWiFi();

    // --- Startup feedback ---
    blinkLED(3, 200);
    beepBuzzer(2, 100);

    Serial.println("\n[SYSTEM] Ready! Sending data every " + String(SEND_INTERVAL) + "ms");
    Serial.println("============================================\n");
}

// ============================================================
//  MAIN LOOP
// ============================================================

void loop() {
    // Read all sensors
    readMAX30102();
    readMPU6050();
    readGPS();

    // Local emergency checks (no network delay)
    checkLocalEmergency();

    // Send data to backend periodically
    unsigned long now = millis();
    if (now - lastSendTime >= SEND_INTERVAL) {
        lastSendTime = now;

        if (wifiConnected) {
            sendSensorData();
        } else {
            Serial.println("[WIFI] Disconnected — attempting reconnect...");
            connectWiFi();
        }
    }

    // Poll for commands from backend
    if (now - lastCmdPollTime >= CMD_POLL_INTERVAL) {
        lastCmdPollTime = now;
        if (wifiConnected) {
            pollCommands();
        }
    }

    // Update buzzer/LED based on state
    updateOutputs();
}

// ============================================================
//  SENSOR READING FUNCTIONS
// ============================================================

void readMAX30102() {
    long irValue = particleSensor.getIR();

    if (irValue > 50000) {
        // Finger is on the sensor
        if (checkForBeat(irValue)) {
            long delta = millis() - lastBeat;
            lastBeat = millis();

            beatsPerMinute = 60.0 / (delta / 1000.0);

            if (beatsPerMinute > 20 && beatsPerMinute < 255) {
                rates[rateSpot++] = (byte)beatsPerMinute;
                rateSpot %= RATE_SIZE;

                // Average the readings
                beatAvg = 0;
                for (byte x = 0; x < RATE_SIZE; x++) {
                    beatAvg += rates[x];
                }
                beatAvg /= RATE_SIZE;
                heartRate = beatAvg;
            }
        }

        // Simple SpO2 estimation (for demo — real SpO2 needs red+IR ratio)
        // In production, use the SparkFun SpO2 algorithm
        long redValue = particleSensor.getRed();
        if (redValue > 0 && irValue > 0) {
            float ratio = (float)redValue / (float)irValue;
            // Simplified SpO2 estimation
            spO2 = constrain(110.0 - 25.0 * ratio, 70, 100);
        }
    } else {
        // No finger detected
        heartRate = 0;
        spO2 = 0;
    }
}

void readMPU6050() {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // Acceleration in g (divide by 9.81 to convert from m/s²)
    accelX = a.acceleration.x / 9.81;
    accelY = a.acceleration.y / 9.81;
    accelZ = a.acceleration.z / 9.81;

    // Gyroscope in degrees/second
    gyroX = g.gyro.x * (180.0 / PI);
    gyroY = g.gyro.y * (180.0 / PI);
    gyroZ = g.gyro.z * (180.0 / PI);
}

void readGPS() {
    while (gpsSerial.available() > 0) {
        char c = gpsSerial.read();
        gps.encode(c);
    }

    if (gps.location.isValid()) {
        latitude = gps.location.lat();
        longitude = gps.location.lng();
        gpsFix = true;
    } else {
        gpsFix = false;
    }

    if (gps.speed.isValid()) {
        speedKmh = gps.speed.kmph();
    }
}

// ============================================================
//  LOCAL EMERGENCY DETECTION
// ============================================================

void checkLocalEmergency() {
    // --- Heart rate emergency (bypass network) ---
    if (heartRate > 0) {
        if (heartRate >= HR_EMERGENCY) {
            Serial.println("[EMERGENCY] Heart rate extremely high: " + String(heartRate) + " BPM");
            triggerLocalEmergency();
        } else if (heartRate <= HR_CRITICAL_LOW) {
            Serial.println("[EMERGENCY] Heart rate critically low: " + String(heartRate) + " BPM");
            triggerLocalEmergency();
        }
    }

    // --- SpO2 emergency ---
    if (spO2 > 0 && spO2 <= SPO2_CRITICAL) {
        Serial.println("[EMERGENCY] SpO2 critically low: " + String(spO2) + "%");
        triggerLocalEmergency();
    }

    // --- Impact detection (crash) ---
    float totalAccel = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ);
    float deviation = abs(totalAccel - 1.0);

    if (deviation >= 4.0) {
        Serial.println("[EMERGENCY] Severe crash detected! Accel deviation: " + String(deviation) + "g");
        triggerLocalEmergency();
    } else if (deviation >= 2.5) {
        Serial.println("[CRITICAL] Impact detected! Accel deviation: " + String(deviation) + "g");
        activateBuzzer(true);
        blinkLED(5, 100);
    }

    // --- Rollover detection ---
    if (accelZ > -0.5 && accelZ < 0) {
        Serial.println("[EMERGENCY] Possible rollover! Z-axis: " + String(accelZ) + "g");
        triggerLocalEmergency();
    }
}

void triggerLocalEmergency() {
    Serial.println("!!! LOCAL EMERGENCY TRIGGERED !!!");
    stopMotor();
    activateBuzzer(true);
    digitalWrite(LED_PIN, HIGH);
    ledActive = true;
}

// ============================================================
//  MOTOR / BUZZER / LED CONTROL
// ============================================================

void stopMotor() {
    if (motorRunning) {
        Serial.println("[MOTOR] Stopping motor!");
        digitalWrite(MOTOR_PIN, LOW);
        motorRunning = false;
    }
}

void startMotor() {
    if (!motorRunning) {
        Serial.println("[MOTOR] Starting motor");
        digitalWrite(MOTOR_PIN, HIGH);
        motorRunning = true;
    }
}

void activateBuzzer(bool active) {
    buzzerActive = active;
}

void updateOutputs() {
    // Buzzer pattern
    if (buzzerActive) {
        // Alternating beep pattern
        unsigned long t = millis() % 1000;
        digitalWrite(BUZZER_PIN, (t < 500) ? HIGH : LOW);
    } else {
        digitalWrite(BUZZER_PIN, LOW);
    }

    // LED blink when active
    if (ledActive && !motorRunning) {
        unsigned long t = millis() % 400;
        digitalWrite(LED_PIN, (t < 200) ? HIGH : LOW);
    }
}

void blinkLED(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        delay(delayMs);
    }
}

void beepBuzzer(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(delayMs);
        digitalWrite(BUZZER_PIN, LOW);
        delay(delayMs);
    }
}

// ============================================================
//  WIFI
// ============================================================

void connectWiFi() {
    Serial.print("[WIFI] Connecting to " + String(WIFI_SSID) + "...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println(" Connected!");
        Serial.println("[WIFI] IP: " + WiFi.localIP().toString());
    } else {
        wifiConnected = false;
        Serial.println(" FAILED!");
    }
}

// ============================================================
//  HTTP COMMUNICATION
// ============================================================

void sendSensorData() {
    if (WiFi.status() != WL_CONNECTED) {
        wifiConnected = false;
        return;
    }

    HTTPClient http;
    String url = String(SERVER_URL) + String(SENSOR_ENDPOINT);
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    // Build JSON payload
    StaticJsonDocument<512> doc;
    doc["heart_rate_bpm"] = heartRate;
    doc["spo2_percent"] = spO2;
    doc["accel_x"] = accelX;
    doc["accel_y"] = accelY;
    doc["accel_z"] = accelZ;
    doc["gyro_x"] = gyroX;
    doc["gyro_y"] = gyroY;
    doc["gyro_z"] = gyroZ;
    doc["latitude"] = latitude;
    doc["longitude"] = longitude;
    doc["speed_kmh"] = speedKmh;
    doc["gps_fix"] = gpsFix;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    // Send POST request
    int httpCode = http.POST(jsonPayload);

    if (httpCode > 0) {
        String response = http.getString();

        // Parse response for commands
        StaticJsonDocument<512> respDoc;
        DeserializationError error = deserializeJson(respDoc, response);

        if (!error) {
            const char* command = respDoc["command"];
            if (command != nullptr) {
                executeCommand(String(command));
            }

            const char* alertLevel = respDoc["alert_level"];
            if (alertLevel != nullptr) {
                Serial.println("[SERVER] Alert Level: " + String(alertLevel));
            }
        }
    } else {
        Serial.println("[HTTP] POST failed, error: " + http.errorToString(httpCode));
    }

    http.end();
}

void pollCommands() {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String url = String(SERVER_URL) + String(CMD_ENDPOINT);
    http.begin(url);

    int httpCode = http.GET();
    if (httpCode > 0) {
        String response = http.getString();
        StaticJsonDocument<256> doc;
        DeserializationError error = deserializeJson(doc, response);

        if (!error) {
            const char* command = doc["command"];
            if (command != nullptr) {
                executeCommand(String(command));
            }
        }
    }

    http.end();
}

void executeCommand(String command) {
    Serial.println("[CMD] Executing: " + command);

    if (command == "STOP_MOTOR") {
        stopMotor();
        activateBuzzer(true);
        ledActive = true;
    } else if (command == "START_MOTOR") {
        startMotor();
        activateBuzzer(false);
        ledActive = false;
    } else if (command == "ACTIVATE_BUZZER") {
        activateBuzzer(true);
    } else if (command == "DEACTIVATE_BUZZER") {
        activateBuzzer(false);
    } else if (command == "ACTIVATE_LED") {
        ledActive = true;
        digitalWrite(LED_PIN, HIGH);
    } else if (command == "DEACTIVATE_LED") {
        ledActive = false;
        digitalWrite(LED_PIN, LOW);
    } else if (command == "RESET") {
        Serial.println("[CMD] System RESET");
        startMotor();
        activateBuzzer(false);
        ledActive = false;
        digitalWrite(LED_PIN, LOW);
        digitalWrite(BUZZER_PIN, LOW);
    } else {
        Serial.println("[CMD] Unknown command: " + command);
    }
}
