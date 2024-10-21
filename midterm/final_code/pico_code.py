import time
import asyncio
from machine import ADC, Pin, PWM
from mqtt import MQTTClient
from BLE_CEEO import Yell
from poor_unfortuante import midi_data  # Import the MIDI data from the file
import network

# MIDI commands and settings
NoteOn = 0x90
NoteOff = 0x80
velocity = {'off': 0, 'ppp': 20, 'mp': 53, 'f': 80}  # Adjust velocity levels as needed

volume_adjustments = {
    "increase": 10,  # Increase volume by 10
    "decrease": -10  # Decrease volume by 10
}

# Connect to the network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('Tufts_Robot', '')

while wlan.ifconfig()[0] == '0.0.0.0':
    print('.', end=' ')
    time.sleep(1)

print("Connected:", wlan.ifconfig())

# MusicPlayer Class
class MusicPlayer:
    def __init__(self, mqtt_broker, port, mqtt_topic, client_id='ME35_rach_pico'):
        self.current_velocity = velocity['mp']  # Default volume level
        
        # MQTT
        self.mqtt_broker = mqtt_broker
        self.port = port
        self.mqtt_topic = mqtt_topic
        self.client_id = client_id
        self.client = MQTTClient(self.client_id, self.mqtt_broker, self.port, keepalive=60)

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
        self.led_pins = [14, 15, 16, 17]
        self.leds = [Pin(pin, Pin.OUT) for pin in self.led_pins]
        
        # Status booleans
        self.paused = True  # Start paused
        self.active = False  # System is inactive initially

    # Check photoresistor values - pause/restart
    async def check_light_levels(self):
        while True:
            if self.active:  # Only check light levels if the system is active
                light_level = self.photoresistor.read_u16()
                print("Light Level:", light_level)
                if light_level < 10000:
                    print("Dark detected! Pausing tasks...")
                    self.paused = True
                else:
                    print("Light detected! Resuming tasks...")
                    self.paused = False
            await asyncio.sleep(0.5)

    # Send singular midi messages
    async def send_midi(self, note, velocity, note_on=True):
        if self.active:
            channel = 0
            command = NoteOn if note_on else NoteOff
            timestamp_ms = time.ticks_ms()
            tsM = (timestamp_ms >> 7 & 0b111111) | 0x80
            tsL = 0x80 | (timestamp_ms & 0b1111111)

            midi_message = bytes([tsM, tsL, command | channel, note, velocity])
            self.p.send(midi_message)

    # Play a song
    async def play_song(self):
        if self.active:
            for event in midi_data:
                while self.paused:
                    await asyncio.sleep(0.1)

                msg_type, note, velocity, duration = event
                if msg_type == 'note_on':
                    await self.send_midi(note, self.current_velocity, note_on=True)
                elif msg_type == 'note_off':
                    await self.send_midi(note, velocity, note_on=False)

                await asyncio.sleep(duration)
                
        # MQTT handler
    def mqtt_callback(self, topic, msg):
        payload = msg.decode()
        print(f"Received message on {topic}: {payload}")

        if payload == "start":
            print("Starting system...")
            self.active = True
            self.paused = False
            self.turn_on_leds()  # Turn on all LEDs
        elif payload == "stop":
            print("Stopping system...")
            self.active = False
            self.paused = True
            self.turn_off_leds()  # Turn off all LEDs
        elif payload == "song":
            if self.active:
                print("Playing song...")
                asyncio.create_task(self.play_song())  # Play song asynchronously
        elif payload == "note":
            if self.active:
                print("Playing a single note...")
                asyncio.create_task(self.send_midi(60, self.current_velocity, note_on=True))
                await asyncio.sleep(0.5)  # Short delay before turning off the note
                asyncio.create_task(self.send_midi(60, self.current_velocity, note_on=False))
        elif payload in volume_adjustments:  # Check for loud or quiet
            if payload == "loud":
                self.current_velocity = min(127, self.current_velocity + volume_adjustments[payload])  # Limit to 127
                print(f"Volume increased to {self.current_velocity}.")
            elif payload == "quiet":
                self.current_velocity = max(0, self.current_velocity + volume_adjustments[payload])  # Limit to 0
                print(f"Volume decreased to {self.current_velocity}.")

    # Non-blocking MQTT message checker
    async def mqtt_message_loop(self):
        while True:
            self.client.check_msg()  # Check for incoming messages
            await asyncio.sleep(1)  # Poll MQTT every second

    async def connect_and_subscribe(self):
        try:
            self.client.set_callback(self.mqtt_callback)
            self.client.connect()
            print(f'Connected to {self.mqtt_broker} MQTT broker')
            self.client.subscribe(self.mqtt_topic.encode())
        except OSError as e:
            print(f"Failed to connect to MQTT broker: {e}")
            await asyncio.sleep(5)
            await self.connect_and_subscribe()
    
    # Set servo angle
    def set_servo_angle(self, angle):
        min_duty = 1000  # 1ms pulse (0 degrees)
        max_duty = 9000  # 2ms pulse (180 degrees)
        duty = min_duty + (max_duty - min_duty) * angle // 180
        self.servo_pwm.duty_u16(duty)

    # Move servo
    async def move_servo_async(self, speed):
        # Move servo from 0 to 180 degrees
        for angle in range(0, 180, 5): 
            while self.paused:
                await asyncio.sleep(0.1)

            await self.set_servo_angle(angle)
            await asyncio.sleep(speed)
        
        await asyncio.sleep(0.1)  # Pause at 180 degrees

        # Move servo back from 180 to 0 degrees
        for angle in range(180, 0, -5): 
            while self.paused:
                await asyncio.sleep(0.1)

            await self.set_servo_angle(angle)
            await asyncio.sleep(speed)

        await asyncio.sleep(0.1)  # Pause at 0 degrees

    # Get distance
    def get_distance(self):
        self.sig.init(Pin.OUT)
        self.sig.low()
        await asyncio.sleep(0.02)
        self.sig.high()
        await asyncio.sleep(0.10)
        self.sig.low()
        
        self.sig.init(Pin.IN)
        
        # Measure 
        pulse_duration = time_pulse_us(self.sig, 1)

        # Calculate distance in centimeters (speed of sound = 34300 cm/s)
        distance_cm = (pulse_duration * 0.0343) / 2
        return distance_cm

    # Adjust servo speed from dist
    async def adjust_servo_speed_based_on_distance(self):
        while True:
            if self.active == True:
                while self.paused: 
                    await asyncio.sleep(0.1)

                distance = await self.get_distance()
                print(f"Distance: {distance} cm")

                if distance < 10:  # Close distance
                    speed = 0.09  # Slower speed
                elif distance < 20:  # Medium distance
                    speed = 0.05  # Medium speed
                else:  # Far distance
                    speed = 0.01  # Faster speed

                await self.move_servo_async(speed)
                await asyncio.sleep(0.5)

    # Read sound levels
    async def monitor_sound_levels(self):
        while True:
            if self.active == True:
                while self.paused: 
                    await asyncio.sleep(0.1)

                sound_level = self.sound_sensor.read_u16()
                print("Sound Level:", sound_level)

                # Control LEDs based on sound level
                if sound_level > 10000: 
                    flash_speed = 0.1  # Fast flash
                    self.turn_on_leds()
                else:
                    flash_speed = 0.5  # Slow flash
                    self.turn_off_leds()

                # Flash LEDs
                for led in self.leds:
                    led.high()
                await asyncio.sleep(flash_speed)
                for led in self.leds:
                    led.low()
                await asyncio.sleep(flash_speed)
    
    # Turn on LEDs
    def turn_on_leds(self):
        for led in self.leds:
            led.high()

    # Turn off LEDs
    def turn_off_leds(self):
        for led in self.leds:
            led.low()

    # Disconnect
    async def disconnect(self):
        print("Disconnecting...")
        self.turn_off_leds()
        self.p.disconnect()
        self.client.disconnect()

# Main function to run the player
async def main():
    player = MusicPlayer(mqtt_broker='10.243.82.33', port=1883, mqtt_topic='ME35-24/mermaid')
    await player.connect_and_subscribe()

    # Start tasks
    asyncio.create_task(player.check_light_levels())
    asyncio.create_task(player.mqtt_message_loop())
    
    try:
        while True:
            await asyncio.sleep(.1)  # Keep the main loop running
    except KeyboardInterrupt:
        await player.disconnect()
        print("Program interrupted.")

try:
    asyncio.run(main())
except Exception as e:
    print(f"An error occurred: {e}")

