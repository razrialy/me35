# The base of this code comes from code used from the previous
# nightlight project that was written by Aengus Kennedy & Rachael Azrialy.

# The code was edited to add more features to the nightlight and was added
# by Rachael Azrialy.

from machine import Pin, PWM, I2C
import neopixel
import time
import asyncio
from mqtt import MQTTClient
import struct

threadsleep = 0.1

# This section connects the board to wifi
if True:
    import network

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('Tufts_Robot', '')

    print('Wi-Fi connection pending', end='')
    while wlan.ifconfig()[0] == '0.0.0.0':
        print('.', end='')
        time.sleep(1)

    print('\nWi-Fi connection successful: {}'.format(wlan.ifconfig()))


class Acceleration:
    def __init__(self, scl, sda, addr=0x62):
        self.addr = addr
        self.i2c = I2C(0, scl=scl, sda=sda, freq=100000)
        self.connected = False
        if self.is_connected():
            print('connected')
            self.write_byte(0x11, 2)  # Start data stream

    def is_connected(self):
        options = self.i2c.scan()
        print(options)
        self.connected = self.addr in options
        return self.connected

    def read_accel(self):
        buffer = self.i2c.readfrom_mem(self.addr, 0x02, 6)  # Read 6 bytes starting at memory address 2
        return struct.unpack('<hhh', buffer)

    def write_byte(self, cmd, value):
        self.i2c.writeto_mem(self.addr, cmd, value.to_bytes(1, 'little'))


class NightLightAsync:
    def __init__(self):
        self.current_color_index = 0
        brightness = 255
        self.colors = [
            (brightness, 0, 0),       # Red
            (brightness, brightness, 0),    # Yellow
            (0, brightness, 0),      # Green
            (0, 0, brightness),      # Blue
            (brightness // 2, 0, brightness // 2),    # Purple
            (brightness, brightness, brightness)  # White
        ]
        self.running = False
        self.buzzer = PWM(Pin('GPIO18', Pin.OUT))
        self.buzzer.freq(880)
        self.buzzer.duty_u16(0)
        self.button = Pin(28, Pin.IN, Pin.PULL_DOWN)  # External button on GPIO 28
        self.neopixel = neopixel.NeoPixel(Pin(28), 1)
        self.leds = [Pin(pin, Pin.OUT) for pin in [27, 22, 17]]
        
        # Setup Stepper Motor (Pin 15)
        self.stepper = PWM(Pin(15))
        self.stepper.freq(50)  # Set frequency for stepper motor

        # Accelerometer setup
        self.accel = Acceleration(Pin('GPIO5', Pin.OUT), Pin('GPIO4', Pin.OUT))

        # Store initial reading
        self.last_reading = self.accel.read_accel()

        # Movement threshold
        self.threshold = 2000  # Adjust this to be more or less sensitive

    async def breathe(self, gpio_pin):
        led = PWM(Pin(gpio_pin, Pin.OUT))
        led.freq(50)
        while True:
            if self.running:
                for i in tuple(range(0, 65535, 500)) + tuple(range(65535, 0, -500)):
                    led.duty_u16(i)
                    await asyncio.sleep(0.01)
            else:
                led.duty_u16(0)
            await asyncio.sleep(threadsleep)

    async def beep(self, duration=0.25, freq=880):
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(1000)
        await asyncio.sleep(duration)
        self.buzzer.duty_u16(0)

    async def play_thriller(self):
        # Approximated melody for the intro of "Thriller"
        notes = [
            (659, 0.5), (622, 0.5), (587, 0.5), (466, 1.0),  # First part of intro
            (659, 0.5), (622, 0.5), (587, 0.5), (466, 1.0),  # Repeat
              # Second part of intro
        ]
        for freq, duration in notes:
            await self.beep(duration=duration, freq=freq)

    async def spin_motor(self, duration=5):
        for i in range(2):
            # Rotate the motor in a full sweep
            for angle in range(0, 181, 10):
                self.set_servo_angle(angle)
                await asyncio.sleep(0.05)
            
            for angle in range(180, 4, -10):
                self.set_servo_angle(angle)
                await asyncio.sleep(0.05)
            self.stepper.deinit()

    def set_servo_angle(self, angle):
        # Map angle (0-180) to PWM duty cycle (1000-9000)
        duty = 1000 + int((angle / 180) * 8000)
        self.stepper.duty_u16(duty)

    def state_leds(self, state):
        """ Turn LEDs on or off based on the state. """
        for led in self.leds:
            led.value(1 if state else 0)

    async def cycle_neopixel(self):
        while True:
            if self.running:
                self.neopixel[0] = self.colors[self.current_color_index]
                self.neopixel.write()

                # Turn on additional LEDs when neopixel is on
                self.state_leds(True)

                if self.button.value() == 1:  # External button pressed
                    self.current_color_index = (self.current_color_index + 1) % len(self.colors)

            else:
                self.neopixel[0] = (0, 0, 0)
                self.neopixel.write()

                # Turn off additional LEDs when neopixel is off
                self.state_leds(False)

                self.buzzer.duty_u16(0)

            await asyncio.sleep(threadsleep)

    async def check_acceleration(self):
        last_accel = self.accel.read_accel()
        
        while True:
            current_reading = self.accel.read_accel()

            # Check if the difference between current and last reading exceeds the threshold
            if (abs(current_reading[0] - last_accel[0]) > self.threshold or
                abs(current_reading[1] - last_accel[1]) > self.threshold or
                abs(current_reading[2] - last_accel[2]) > self.threshold):
                if self.running:
                    # Play "Thriller" and spin motor
                    thriller_task = asyncio.create_task(self.play_thriller())
                    motor_task = asyncio.create_task(self.spin_motor(duration=5))

                    await asyncio.gather(thriller_task, motor_task)

            # Update last reading
            last_accel = current_reading
            await asyncio.sleep(0.1)
    
    async def mqtt_subscribe(self):
        mqtt_broker = 'broker.hivemq.com'
        port = 1883
        topic = 'ME35-24/spooky'

        def callback(topic, msg):
            topic, msg = topic.decode(), msg.decode()
            print(topic, msg)
            if msg == 'start':
                self.running = True
            elif msg == 'stop':
                self.running = False
                
        client = MQTTClient('ME35_chris', mqtt_broker, port, keepalive=60)
        client.set_callback(callback)
        client.connect()
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            await asyncio.sleep(threadsleep)

if True:
    nl = NightLightAsync()

    thread = asyncio.get_event_loop()

    thread.create_task(nl.breathe('GPIO0'))
    thread.create_task(nl.cycle_neopixel())
    thread.create_task(nl.check_acceleration())
    thread.create_task(nl.mqtt_subscribe())

    thread.run_forever()

