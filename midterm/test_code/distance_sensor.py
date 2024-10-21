from machine import Pin, time_pulse_us
import time

# Define SIG pin (for both TRIG and ECHO)
sig = Pin(5, Pin.OUT)

# Function to measure distance
def get_distance():
    # Send a 10us pulse to trigger the ultrasonic module
    sig.init(Pin.OUT)  # Set pin to output mode
    sig.low()
    time.sleep_us(2)
    sig.high()
    time.sleep_us(10)
    sig.low()
    
    # Wait for the echo signal
    sig.init(Pin.IN)  # Set pin to input mode to listen for echo
    
    # Measure the duration of the echo pulse in microseconds
    pulse_duration = time_pulse_us(sig, 1)  # Wait for the SIG pin to go HIGH

    # Calculate distance in centimeters (speed of sound = 34300 cm/s)
    distance_cm = (pulse_duration * 0.0343) / 2
    
    return distance_cm

# Main loop to continuously read and print the distance
while True:
    distance = get_distance()
    print("Distance:", distance, "cm")
    
    time.sleep(0.5)  # Delay between measurements

