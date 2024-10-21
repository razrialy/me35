import machine
import time

# Set up the photoresistor pin (Pin 28) as an ADC input
photoresistor = machine.ADC(28)

while True:
    # Read the analog value from the photoresistor
    photoresistor_value = photoresistor.read_u16()  # Get a 16-bit ADC value (0-65535)

    # Convert the value to a voltage (optional, depending on your use case)
    voltage = photoresistor_value * (3.3 / 65535)  # Assuming 3.3V reference voltage
    
    # Delay for a bit before the next reading
    time.sleep(0.5)
