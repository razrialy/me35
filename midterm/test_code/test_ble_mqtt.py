import time
import asyncio
from machine import ADC, Pin, PWM
from mqtt import MQTTClient
from BLE_CEEO import Yell
from poor_unfortuante import midi_data  # Import the MIDI data from the file
import network

# Connect to the network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('WIFI NAME', 'PASSWORD')

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

class MusicBox:
    def __init__(self):
        #self.current_velocity = velocity['mp']  # Default volume level
        
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
            elif msg == 'loud':
                if self.active == True and self.paused == False:
                    print('increase volume')
                    self.current_velocity = min(127, self.current_velocity + volume_adjustments[payload])  # Limit to 127   
            elif msg == 'quiet':
                if self.active == True and self.paused == False:
                    print('decrease volume')
                    self.current_velocity = max(0, self.current_velocity + volume_adjustments[payload])
            elif msg == 'song':
                if self.active == True and self.paused == False:
                    print('song')
                    asyncio.create_task(self.play_song())  
            elif msg == 'note':
                if self.active == True and self.paused == False:
                    print('note')
                    asyncio.create_task(self.send_midi(60, self.current_velocity, note_on=True))
                    await asyncio.sleep(0.5)  # Short delay before turning off the note
                    asyncio.create_task(self.send_midi(60, self.current_velocity, note_on=False))

        client.set_callback(callback)
        client.connect()
        print('connected - subscribe')
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            await asyncio.sleep(0.1)
            
#     def mqtt_publish(self):
#         client.connect()
#         print('connected - publish')
#         msg = 'start'
#         client.publish(topic_pub.encode(),msg.encode())
        
    def leds_on(self):
        for led in self.leds:
            led.high()

    # Turn off LEDs
    def leds_off(self):
        for led in self.leds:
            led.low()

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
        
        
while True:
    music = MusicBox()

    thread = asyncio.get_event_loop()

    thread.create_task(music.mqtt_subscribe())

    thread.run_forever()