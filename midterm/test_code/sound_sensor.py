from machine import ADC, Pin
import time

# Initialize ADC on pin GP27 (which corresponds to ADC1)
sound_sensor = ADC(Pin(27))

while True:
    # Read the analog value (12-bit resolution: 0-4095)
    sound_level = sound_sensor.read_u16()
    # Print the sound level value
    print("Sound Level:", sound_level)
    # Add a small delay
    time.sleep(0.1)
