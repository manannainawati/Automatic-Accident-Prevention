#include <Wire.h>
#include <MPU6050_tockn.h>
#include "MAX30105.h"
#include "heartRate.h"

MAX30105 particleSensor;
MPU6050 mpu6050(Wire);

const int buzzer = 8;
const int led = 9;

long lastBeat = 0;
float bpm = 0;

float ax, ay, az;

String lastStatus = "NORMAL";

unsigned long lastSend = 0;
int sendInterval = 200;   // send BPM every 200 ms

void setup()
{
  Serial.begin(115200);
  Wire.begin();

  pinMode(buzzer, OUTPUT);
  pinMode(led, OUTPUT);

  mpu6050.begin();
  mpu6050.calcGyroOffsets(true);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
  {
    Serial.println("STATUS:ERROR");
    while (1);
  }

  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);

  Serial.println("STATUS:NORMAL");
}

void loop()
{
  long irValue = particleSensor.getIR();

  if (checkForBeat(irValue))
  {
    long delta = millis() - lastBeat;
    lastBeat = millis();
    bpm = 60 / (delta / 1000.0);
  }

  mpu6050.update();

  ax = mpu6050.getAccX();
  ay = mpu6050.getAccY();
  az = mpu6050.getAccZ();

  float totalAcc = sqrt(ax * ax + ay * ay + az * az);

  bool abnormalMotion = totalAcc > 2;

  bool medicalEmergency = (bpm > 120 || abnormalMotion);

  if (medicalEmergency)
  {
    digitalWrite(led, HIGH);
    tone(buzzer, 2500);
  }
  else
  {
    digitalWrite(led, LOW);
    noTone(buzzer);
  }

  String currentStatus = medicalEmergency ? "MEDICAL" : "NORMAL";

  if (currentStatus != lastStatus)
  {
    Serial.print("STATUS:");
    Serial.print(currentStatus);
    Serial.print(",BPM:");
    Serial.println((int)bpm);

    lastStatus = currentStatus;
  }

  // send BPM regularly
  if (millis() - lastSend > sendInterval)
  {
    lastSend = millis();

    Serial.print("BPM:");
    Serial.println((int)bpm);
  }
}
