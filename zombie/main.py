from Tufts_ble import Yell, Sniff
import time
import neopixel
from machine import Pin
from machine import Pin, PWM
import time

# Set the NeoPixel LED color
def set_neopixel_state(pin, color):
    led = neopixel.NeoPixel(Pin(pin), 1)
    led[0] = color
    led.write()

def buzzer(frequency=440, duration=1):
    buzzer_pwm = PWM(Pin(18, Pin.OUT))  # GPIO18 pin
    buzzer_pwm.freq(frequency)
    buzzer_pwm.duty_u16(1000)
    time.sleep(duration)
    buzzer_pwm.duty_u16(0)
    
    buzzer_pwm.deinit()

# Define the GPIO pins for the first four LEDs
led_pins = [Pin(i, Pin.OUT) for i in range(4)]  # Pins 0, 1, 2, 3

def display_binary(num):
    # Ensure the number is between 0 and 13
    if num < 0 or num > 13:
        print("Number must be between 0 and 13.")
        return
    
    # Convert number to binary and light up LEDs accordingly
    binary_str = f"{num:04b}"  # Format number as 4-bit binary
    for i in range(4):
        led_pins[i].value(int(binary_str[i]))  # Set LED state based on binary
        
# Zombie
class PeripheralDevice:
    def __init__(self, message):
        self.message = message  # The message will be the number, e.g., '!9'

    # Advertise peripheral using BLE
    def advertise(self):
        try:
            self.device = Yell()
            print(f'Peripheral advertising: {self.message}')
            set_neopixel_state(28, (255, 0, 0))  # Red neopixel for zombie

            # Advertise only the message (number)
            self.device.advertise(self.message)
            
            buzzer(frequency=440, duration=1)
        except Exception as e:
            print(f"Error in peripheral advertising: {e}")
        finally:
            self.stop_advertising()

    # Stop advertising the message
    def stop_advertising(self):
        if self.device:
            self.device.stop_advertising()
            set_neopixel_state(28, (0, 0, 0))  # Turn off neopixel
            print(f'Peripheral stopped advertising')




# Human
class CentralDevice:
    def __init__(self):
        self.device = Sniff('!', verbose = True)
        self.proximity_start_time = None
        self.prox_thresh = -70
        self.close_thresh = -80
        self.last_message = ""
        
        self.tag_count = 0  # Count of tags received
        self.tags = [0] * 14  # Array to track player tags
        self.is_tagged = False  # To track if the player is tagged
        self.in_proximity = False  # Track if currently in proximity
        
    def listen(self):
        self.device.scan(0)   # 0ms = scans forever 
        for i in range(100):
            latest = self.device.last
            rssi = self.device.get_rssi()
            if latest:
                self.device.last='' # clear the flag for the next advertisement
                print('Got: ' + latest + f' with RSSI: {rssi}')
                if latest != "!12":
                    self.check_proximity(latest, int(rssi))
            time.sleep(1)
        
        self.stop_listening()
    
    def check_proximity(self, latest, rssi):
        current_time = time.time()

        # Check if in proximity
        if rssi >= self.prox_thresh:
            if self.last_message == latest:  # Check if the same message is received
                if self.proximity_start_time is None:
                    print("Starting proximity timer for the same message.")
                    self.proximity_start_time = current_time  # Start timer
                else:
                    elapsed_time = current_time - self.proximity_start_time
                    print(f"Elapsed Time in Proximity: {elapsed_time:.2f} seconds")
                    if elapsed_time >= 3:  # Check if 3 seconds have passed
                        if not self.is_tagged:  # Only tag if not already tagged
                            number = int(self.last_message[1:])
                            self.tags[number] += 1
                            print(f'Tag count: {self.tags}')
                            
                            self.proximity_start_time = current_time
                            
                            if self.tags[number] >= 3:  # Become the next number if tagged 3 times
                                self.is_tagged = True
                                self.become_zombie(number)  # Pass the new zombie number
            else:  # If the message is different, update the last message
                self.last_message = latest  # Update last message
                self.proximity_start_time = None
        elif self.last_message == latest:  # Only reset timer if the same number goes out of range
            print("Same number went out of range; resetting timer.")
            self.proximity_start_time = None  # Reset timer
            self.last_message = None  # Reset last message

        # Check for close proximity status
        if rssi >= self.close_thresh:
            set_neopixel_state(28, (255, 255, 0))  # Yellow for close proximity
        else:
            set_neopixel_state(28, (0, 255, 0))
    
    def become_zombie(self, number):
        print(f"Becoming a zombie and broadcasting: !{number}")
        self.stop_listening()
        peripheral_device = PeripheralDevice(f'!{number}')
        while True:
            peripheral_device.advertise()  # Switch to peripheral mode and start advertising
            display_binary(number)
    
    def stop_listening(self):
        self.device.stop_scan()
        

# Initialize Peripheral and advertise
peripheral_device = PeripheralDevice('!9')  # Only pass the message (number)
while True:
    peripheral_device.advertise()
    time.sleep(1)


"""
# Initialize Central and start listening for advertisements
central_device = CentralDevice()
while True:
    central_device.listen()
    time.sleep(1)
"""

