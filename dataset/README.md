# Dataset & Threshold Configuration

## Files

### `heart_rate_thresholds.json`
Configurable thresholds for MAX30102 sensor readings:
- **Heart Rate (BPM)**: Normal (60-100), Warning (50-59 / 101-120), Critical (<50 / 121-180), Emergency (>180)
- **SpO2 (%)**: Normal (95-100), Warning (90-94), Critical (80-89), Emergency (<80)
- **Heart Rate Variability**: Sudden change detection (30+ BPM in 5 seconds)
- **Drowsiness Correlation**: Gradual HR drop pattern (15+ BPM over 30 seconds)

### `mpu6050_thresholds.json`
Configurable thresholds for MPU6050 sensor readings:
- **Acceleration (g)**: Normal driving (±0.3g), Harsh braking (0.6g), Impact (2.5g), Severe crash (4.0g)
- **Gyroscope (°/s)**: Normal (±30-45°/s), Sudden spin (120°/s), Head tilt drowsiness (15°/s sustained)
- **Composite Scores**: Combined acceleration + gyroscope for event severity classification

### `sample_sensor_data.csv`
1000+ rows of simulated sensor data covering scenarios:
- Normal driving
- Drowsiness onset (gradual HR drop, head tilt)
- Heart attack simulation (sudden HR spike, low SpO2)
- Crash event (high-g impact, rapid spin)
- Post-crash stationary (no vibration, no pulse)

## How to Customize
Edit the JSON threshold files to tune sensitivity for your specific use case. Lower thresholds = more sensitive (more false positives), higher thresholds = less sensitive (may miss events).
