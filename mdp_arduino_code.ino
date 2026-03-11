#include <Wire.h>
#include <MPU6050_tockn.h>
#include "MAX30105.h"
#include "heartRate.h"

MAX30105 particleSensor;
MPU6050 mpu6050(Wire);

const int buzzer = 8;
const int led = 9;

long lastBeat = 0;
float bpm;

float ax, ay, az;

unsigned long lastPrint = 0;
int printInterval = 1000;   // print every 2 seconds

void setup()
{
  Serial.begin(115200);
  Wire.begin();

  pinMode(buzzer, OUTPUT);
  pinMode(led, OUTPUT);

  // MPU6050 setup
  mpu6050.begin();
  mpu6050.calcGyroOffsets(true);

  // MAX30102 setup
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
  {
    Serial.println("MAX30102 not found");
    while (1);
  }

  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);

  Serial.println("System Ready...");
}

void loop()
{
  // -------- HEART RATE --------
  long irValue = particleSensor.getIR();

  if (checkForBeat(irValue))
  {
    long delta = millis() - lastBeat;
    lastBeat = millis();
    bpm = 60 / (delta / 1000.0);
  }

  // -------- MPU6050 --------
  mpu6050.update();

  ax = mpu6050.getAccX();
  ay = mpu6050.getAccY();
  az = mpu6050.getAccZ();

  // -------- JERK DETECTION --------
  bool abnormalMotion = false;
  float totalAcc = sqrt(ax * ax + ay * ay + az * az);

  if (totalAcc > 1.7)
  {
    abnormalMotion = true;
    // Serial.println("JERK DETECTED");
  }

  // -------- ALERT CONDITION --------
  if (bpm > 120 || abnormalMotion)
  {
    digitalWrite(led, HIGH);
    digitalWrite(buzzer, 7000);
  }
  else
  {
    digitalWrite(led, LOW);
    digitalWrite(buzzer, LOW);
  }

  // -------- SERIAL PRINT DELAY --------
  
    lastPrint = millis();

    Serial.println("----------- DATA -----------");

    if (irValue < 50000)
      Serial.println("No finger detected");
    else
    {
      Serial.print("Heart Rate BPM: ");
      Serial.println(bpm);
    }

    Serial.print("ACC X: ");
    Serial.print(ax);

    Serial.print(" | Y: ");
    Serial.print(ay);

    Serial.print(" | Z: ");
    Serial.println(az);

    Serial.print("Total Acceleration: ");
    Serial.println(totalAcc);

    Serial.println("----------------------------");
  
}