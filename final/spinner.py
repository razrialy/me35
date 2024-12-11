import time
from machine import Pin, SoftI2C, ADC
from servo import Servo
import random
import ssd1306
import network
from networking import Networking

# Initialize I2C and OLED screen
i2c = SoftI2C(scl=Pin(7), sda=Pin(6))
screen = ssd1306.SSD1306_I2C(128, 64, i2c)
screen.text('Scorch', 40, 15, 1)  # Display text
screen.text('and', 50, 25, 1)     # Display text
screen.text('Sorcery', 35, 35, 1) # Display text
screen.show()

# Initialize button, networking, and other components
button = Pin(9, Pin.IN)
networking = Networking()
recipient_mac = b'\xff\xff\xff\xff\xff\xff'

reset = 'reset'
individual = 'individual'
together = 'together'

# Initialize potentiometer
pot = ADC(Pin(3))
pot.atten(ADC.ATTN_11DB)  # Set the expected voltage range to 3.3V
print(pot.read())         # Range is 0-4095

# Initialize servo
motor = Servo(Pin(2))

# Function to move servo to a random position
def move_to_random_position():
    target_angle = random.choice([30, 150])
    rotation_time = random.uniform(0.5, 2.0)
    
    motor.write_angle(target_angle)
    time.sleep(rotation_time)
    
    # Stop the servo
    motor.write_angle(90)

# Main program loop
trigger = False
try:
    while True:
        if not button.value():
            networking.aen.send(recipient_mac, reset)
            print("reset")
            move_to_random_position()
            trigger = False
            time.sleep(0.5)
        
        pot_val = pot.read()
        if pot_val < 2000 and trigger == False:
            networking.aen.send(recipient_mac, individual)
            print("individual")
            trigger = True
            time.sleep(0.5)
        elif pot_val > 2000:
            networking.aen.send(recipient_mac, together)
            print("together")
            trigger = True
            time.sleep(0.5)

except KeyboardInterrupt:
    print("Interrupted! Cleaning up...")

finally:
    # Ensure interfaces are deactivated on exit
    print("Finished Spinning")
