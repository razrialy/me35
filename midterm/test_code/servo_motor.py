from machine import Pin, PWM
from time import sleep

# Define servo pin and PWM frequency
servo_pin = 16  # Connect to GPIO pin 16 (not 15)
servo_pwm = PWM(Pin(servo_pin))
Pin(15, Pin.OUT).low

servo_pwm.freq(50)  # Set frequency to 50Hz (standard for servos)

# Function to set servo angle (0 to 180 degrees)
def set_servo_angle(angle):
    # Convert angle to duty cycle value (between 1000 to 9000 us)
    min_duty = 1000  # 1ms pulse (0 degrees)
    max_duty = 9000  # 2ms pulse (180 degrees)
    
    # Scale angle to duty cycle
    duty = min_duty + (max_duty - min_duty) * angle // 180
    servo_pwm.duty_u16(duty)

# Function to move the servo back and forth with adjustable speed
def move_servo(speed):
    # Move servo from 0 to 180 degrees
    for angle in range(0, 181, 5):  # Increment by 5 degrees
        set_servo_angle(angle)
        sleep(speed)  # Use the speed variable to control delay
    
    sleep(0.1)  # Pause at 180 degrees

    # Move servo back from 180 to 0 degrees
    for angle in range(180, -1, -5):  # Decrement by 5 degrees
        set_servo_angle(angle)
        sleep(speed)  # Use the speed variable to control delay
    
    sleep(0.1)  # Pause at 0 degrees

# Set the speed of the servo motion (0.01 is faster, 0.1 is slower)
speed = 0.05  # Adjust this value to change the speed
while True:
    move_servo(0.1)
