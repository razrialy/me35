import time
import uasyncio as asyncio
from machine import ADC, Pin, PWM
from mqtt import MQTTClient
from BLE_CEEO import Yell
from poor_unfortuante import poor  # Import the MIDI data from the file
from part_of_your_world import part
from under_the_sea import under
import network

# Connect to the network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('Tufts_Robot', '')

while wlan.ifconfig()[0] == '0.0.0.0':
    print('.', end=' ')
    time.sleep(1)

print("Connected:", wlan.ifconfig())

mqtt_broker = 'broker.emqx.io'
port = 1883
topic = 'ME35-24/mermaid'
client = MQTTClient('rach_pico', mqtt_broker, port, keepalive=60)

# MIDI commands and settings
NoteOn = 0x90
NoteOff = 0x80
velocity = {'off': 0, 'ppp': 20, 'mp': 53, 'f': 80}  # Adjust velocity levels as needed

volume_adjustments = {
    "increase": 10,  # Increase volume by 10
    "decrease": -10  # Decrease volume by 10
}

note_mapping = {
    'C': 60,
    'D': 62,
    'E': 64,
    'F': 65,
    'G': 67,
    'A': 69,
    'B': 71
}

class MusicBox:
    def __init__(self):
        # Initialize BLE MIDI connection
        self.p = Yell('Rachael', verbose=True, type='midi')
        self.p.connect_up()

        # Servo control setup
        self.servo_pin = 21 
        self.servo_pwm = PWM(Pin(self.servo_pin))
        self.servo_pwm.freq(50)

        # Ultrasonic sensor setup
        self.sig = Pin(5, Pin.OUT)

        # Sound sensor setup
        self.sound_sensor = ADC(Pin(27))

        # Photoresistor setup
        self.photoresistor = ADC(Pin(28))

        # LED pins
        self.led_pins = [13, 15, 16, 17]
        self.leds = [Pin(pin, Pin.OUT) for pin in self.led_pins]
        
        # Status booleans
        self.paused = True  # Start paused
        self.active = False  # System is inactive initially
        self.note = True
        
        self.current_velocity = velocity['mp']  # Default volume level

    async def mqtt_subscribe(self):

        def callback(topic, msg):
            topic, msg = topic.decode(), msg.decode()
            print(topic, msg)
            
            if msg == 'start':
                self.active = True
                self.paused = False
                self.leds_on()
            elif msg == 'stop':
                self.active = False
                self.paused = True
                self.leds_off()
                self.servo_pwm.deinit()
            elif msg == 'loud':
                if self.active and not self.paused:
                    print('increase volume')
                    self.current_velocity = min(127, self.current_velocity + volume_adjustments["increase"])  # Limit to 127   
            elif msg == 'quiet':
                if self.active and not self.paused:
                    print('decrease volume')
                    self.current_velocity = max(0, self.current_velocity + volume_adjustments["decrease"])
            elif msg == 'song':
                self.note = False
                if self.active and not self.paused:
                    print('song')
                    asyncio.create_task(self.play_song([poor, part, under]))  
            elif msg == 'note':
                self.note = True
                if self.active and not self.paused:
                    print('note')
            elif (msg == 'C' or msg == 'D' or msg == 'E' or msg =='F' or msg == 'G'
            or msg == 'A' or msg == 'B') and self.note == True:
                note_number = note_mapping[msg]
                asyncio.create_task(self.send_midi(note_number, self.current_velocity, note_on=True))
                asyncio.create_task(self.stop_note_after(0.1))

        client.set_callback(callback)
        client.connect()
        print('connected - subscribe')
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            await asyncio.sleep(0.01)
            
    async def handle_bluetooth(self):
        while True:
            # Simulate Bluetooth event handling
            await asyncio.sleep(1)
            
    async def stop_note_after(self, delay):
        await asyncio.sleep(delay)
        await self.send_midi(60, self.current_velocity, note_on=False)

    async def send_midi(self, note, velocity, note_on=True):
        if self.active:
            channel = 0
            command = NoteOn if note_on else NoteOff
            timestamp_ms = time.ticks_ms()
            tsM = (timestamp_ms >> 7 & 0b111111) | 0x80
            tsL = 0x80 | (timestamp_ms & 0b1111111)

            midi_message = bytes([tsM, tsL, command | channel, note, velocity])
            self.p.send(midi_message)

    async def play_song(self, midi_data_list):
        if self.active:
            for midi_data in midi_data_list:
                for event in midi_data:
                    while self.paused:
                        await asyncio.sleep(0.1)

                    msg_type, note, velocity, duration = event
                    if msg_type == 'note_on':
                        await self.send_midi(note, self.current_velocity, note_on=True)
                    elif msg_type == 'note_off':
                        await self.send_midi(note, velocity, note_on=False)

                    await asyncio.sleep(duration)
                await asyncio.sleep(2)
                
    def leds_on(self):
        for led in self.leds:
            led.high()

    def leds_off(self):
        for led in self.leds:
            led.low()

    async def check_light_levels(self):
        while True:
            if self.active:
                print("active-light")
                light_level = self.photoresistor.read_u16()
                print("Light Level:", light_level)
                if light_level < 500:
                    print("Dark detected! Pausing tasks...")
                    self.paused = True
                else:
                    print("Light detected! Resuming tasks...")
                    self.paused = False
            await asyncio.sleep(0.5)

    # Set servo angle
    def set_servo_angle(self, angle):
        min_duty = 1000  # 1ms pulse (0 degrees)
        max_duty = 9000  # 2ms pulse (180 degrees)
        duty = min_duty + (max_duty - min_duty) * angle // 180
        self.servo_pwm.duty_u16(duty)

    # Move servo
    async def move_servo_async(self, speed):
        while True:
            # Move servo from 0 to 180 degrees
            for angle in range(2, 178, 5): 
                while self.paused:
                    await asyncio.sleep(0.1)

                self.set_servo_angle(angle)
                await asyncio.sleep(speed)
            
            await asyncio.sleep(0.1)  # Pause at 180 degrees

            # Move servo back from 180 to 0 degrees
            for angle in range(178, 2, -5): 
                while self.paused:
                    await asyncio.sleep(0.1)

                self.set_servo_angle(angle)
                await asyncio.sleep(speed)

            await asyncio.sleep(0.1)  # Pause at 0 degrees

    # Get distance
    async def get_distance(self):
        self.sig.init(Pin.OUT)  # Set pin to output mode
        self.sig.low()
        await asyncio.sleep(.02)  # Sleep for 2 microseconds
        self.sig.high()
        await asyncio.sleep(.010)  # Sleep for 10 microseconds
        self.sig.low()
        
        # Set pin to input mode to listen for echo
        self.sig.init(Pin.IN)

        # Measure the duration of the echo pulse in microseconds
        pulse_start = None
        pulse_end = None

        # Wait for the signal to go high (start of the pulse)
        while not self.sig.value():
            await asyncio.sleep(0)  # Yield control

        # Record the start time using ticks_us
        pulse_start = time.ticks_us()

        # Wait for the signal to go low (end of the pulse)
        while self.sig.value():
            await asyncio.sleep(0)  # Yield control

        # Record the end time using ticks_us
        pulse_end = time.ticks_us()

        # Calculate pulse duration in microseconds
        pulse_duration = time.ticks_diff(pulse_end, pulse_start)

        # Calculate distance in centimeters (speed of sound = 34300 cm/s)
        distance_cm = (pulse_duration * 0.0343) / 2
        
        return distance_cm

    # Adjust servo speed from dist
    async def adjust_servo_dist(self):
        while True:
            #if self.active == True:
            while self.paused: 
                await asyncio.sleep(0.1)

            distance = await self.get_distance()
            print(f"Distance: {distance} cm")

            if distance < 10:  # Close distance
                speed = 0.02  # Slower speed
            elif distance < 20:  # Medium distance
                speed = 0.04  # Medium speed
            else:  # Far distance
                speed = 0.08  # Faster speed

            await self.move_servo_async(speed)
            await asyncio.sleep(0.5)

    # Read sound levels
    async def monitor_sound_levels(self):
        while True:
            #if self.active == True:
            print("sound-active")
            while self.paused: 
                await asyncio.sleep(0.1)

            sound_level = self.sound_sensor.read_u16()
            print("Sound Level:", sound_level)

            # Control LEDs based on sound level
            if sound_level > 10000: 
                flash_speed = 0.1  # Fast flash
                self.leds_on()
            else:
                flash_speed = 0.5  # Slow flash
                self.leds_off()

            # Flash LEDs
            for led in self.leds:
                led.high()
            await asyncio.sleep(flash_speed)
            for led in self.leds:
                led.low()
            await asyncio.sleep(flash_speed)

    async def run(self):
        # Run MQTT, Bluetooth, and light level checking concurrently
        await asyncio.gather(self.mqtt_subscribe(), self.handle_bluetooth(), self.check_light_levels(),
                             self.monitor_sound_levels(), self.adjust_servo_dist())

# Main entry point
music = MusicBox()
asyncio.run(music.run())
