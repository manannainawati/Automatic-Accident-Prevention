# Wiring Diagram — Accident Prevention System

## Components & Pin Connections

```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32 DevKit V1                         │
│                                                                 │
│   3.3V ──────────┬──────────────── MAX30102 VIN                │
│                   ├──────────────── MPU6050 VCC                 │
│                   └──────────────── GPS NEO-6M VCC              │
│                                                                 │
│   GND ───────────┬──────────────── MAX30102 GND                │
│                   ├──────────────── MPU6050 GND                 │
│                   ├──────────────── GPS NEO-6M GND              │
│                   ├──────────────── Buzzer GND                  │
│                   ├──────────────── LED Cathode (-)             │
│                   └──────────────── Motor Driver GND            │
│                                                                 │
│   GPIO 21 (SDA) ─┬──────────────── MAX30102 SDA                │
│                   └──────────────── MPU6050 SDA                 │
│                                                                 │
│   GPIO 22 (SCL) ─┬──────────────── MAX30102 SCL                │
│                   └──────────────── MPU6050 SCL                 │
│                                                                 │
│   GPIO 16 (RX2) ─────────────────── GPS NEO-6M TX              │
│   GPIO 17 (TX2) ─────────────────── GPS NEO-6M RX              │
│                                                                 │
│   GPIO 25 ────────────────────────── Buzzer Signal (+)          │
│   GPIO 26 ──── [220Ω Resistor] ──── LED Anode (+)              │
│   GPIO 27 ────────────────────────── Motor Driver IN1           │
│                                                                 │
│   VIN (5V) ──────────────────────── Motor Driver VCC            │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Connections

### MAX30102 (Heart Rate + SpO2 Sensor)

| MAX30102 Pin | ESP32 Pin | Notes |
|:---:|:---:|:---|
| VIN | 3.3V | Sensor operates at 3.3V |
| GND | GND | Common ground |
| SDA | GPIO 21 | I2C Data (shared with MPU6050) |
| SCL | GPIO 22 | I2C Clock (shared with MPU6050) |
| INT | *Not connected* | Optional interrupt pin |

### MPU6050 (Accelerometer + Gyroscope)

| MPU6050 Pin | ESP32 Pin | Notes |
|:---:|:---:|:---|
| VCC | 3.3V | Sensor operates at 3.3V |
| GND | GND | Common ground |
| SDA | GPIO 21 | I2C Data (shared with MAX30102) |
| SCL | GPIO 22 | I2C Clock (shared with MAX30102) |
| AD0 | GND | Sets I2C address to 0x68 |
| INT | *Not connected* | Optional interrupt |

> **Note:** MAX30102 (address 0x57) and MPU6050 (address 0x68) share the same I2C bus without conflict since they have different addresses.

### GPS NEO-6M

| GPS Pin | ESP32 Pin | Notes |
|:---:|:---:|:---|
| VCC | 3.3V | Use 3.3V (some modules accept 3.3-5V) |
| GND | GND | Common ground |
| TX | GPIO 16 (RX2) | GPS transmits → ESP32 receives |
| RX | GPIO 17 (TX2) | ESP32 transmits → GPS receives |

### Buzzer

| Buzzer Pin | ESP32 Pin | Notes |
|:---:|:---:|:---|
| + (Signal) | GPIO 25 | Active buzzer (HIGH = ON) |
| - (GND) | GND | Common ground |

### LED

| LED Pin | ESP32 Pin | Notes |
|:---:|:---:|:---|
| Anode (+) | GPIO 26 | **Through 220Ω resistor** |
| Cathode (-) | GND | Common ground |

### 100 RPM Gear Motor (via L298N Motor Driver)

| Component | Connection | Notes |
|:---:|:---:|:---|
| Motor Driver IN1 | GPIO 27 | HIGH = Motor ON, LOW = Motor OFF |
| Motor Driver VCC | ESP32 VIN (5V) | Power for logic |
| Motor Driver 12V | External 12V supply | Motor power (adjust for your motor) |
| Motor Driver GND | ESP32 GND | Common ground |
| Motor + | Motor Driver OUT1 | Motor terminal |
| Motor - | Motor Driver OUT2 | Motor terminal |

## Breadboard Layout Tips

1. **Power rails**: Connect ESP32 3.3V to the positive rail and GND to ground rail
2. **I2C bus**: MAX30102 and MPU6050 share SDA/SCL — connect both to the same rows
3. **GPS**: Keep GPS module near a window for satellite reception during testing
4. **Motor driver**: Use an L298N or similar driver — do NOT connect the motor directly to ESP32
5. **Resistor for LED**: Always use a 220Ω (or 330Ω) resistor in series with the LED
6. **Decoupling capacitors**: Add 100µF capacitor across motor driver power to reduce noise
