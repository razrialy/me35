#Used resources/hints Prof Chris Rogers provided
#Used syntax reminders, but not entire lines of code, that ChatGPT provided

from machine import Pin, PWM
import neopixel
import time
import asyncio
from mqtt import MQTTClient

# The threadsleep config controls the 'await asyncio.sleep(threadsleep)' statement
# that appears once in each thread's while True loop to yield processor time to the other processes.
threadsleep = 0.1 

# This section connects the board to Tufts_Wireless.
# It can be disabled to avoid connecting to any Wi-Fi.
if True:
    import network
    import time

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('Tufts_Robot', '')

    print('Wi-Fi connection pending', end = '')
    while wlan.ifconfig()[0] == '0.0.0.0':
        print('.', end='')
        time.sleep(1)

    # We should have a valid IP now via DHCP
    print('\nWi-Fi connection successful: {}'.format(wlan.ifconfig()))



# Most of this class' methods are async, so they can be multithreaded,
# but the class itself does not do the multithreading.
class NightLightAsync:
    # Initialization
    def __init__(self):
        self.current_color_index = 0  #Keep track of current color index
        brightness = 20 #can be 1-255
        self.colors = [
                (brightness, 0, 0),      #Red
                (brightness, brightness, 0),    #Yellow
                (0, brightness, 0),      #Green
                (0, 0, brightness),      #Blue
                (brightness//2, 0, brightness//2),    #Purple
                (brightness, brightness, brightness)]  #White
        self.running = False

        self.buzzer = PWM(Pin('GPIO18', Pin.OUT))
        self.buzzer.freq(880)
        self.buzzer.duty_u16(0)

        self.button = Pin(20, Pin.IN, Pin.PULL_UP)

        self.neopixel = neopixel.NeoPixel(Pin(28), 1)  # Neopixel on GPIO 28

    # This method runs asynchronously forever.
    # It prints out an ascending number every second for testing.
    async def test(self):
        testiter = 0
        while True:
            testiter += 1
            await asyncio.sleep(1)
            print(testiter)
            await asyncio.sleep(threadsleep)

    # This method runs asynchronously forever.
    # If self.running is True, it cycles the LED breathing
    # If self.running is False, it turns off the LED.
    async def breathe(self, gpio_pin):
        led = machine.PWM(machine.Pin(gpio_pin, machine.Pin.OUT))
        led.freq(50)
        while True:
            if self.running:
                for i in tuple(range(0, 65535, 500)) + tuple(range(65535, 0, -500)):
                    led.duty_u16(i)
                    await asyncio.sleep(0.01)
            else:
                led.duty_u16(0)
            await asyncio.sleep(threadsleep)

    # This method runs asynchronously for 0.25 seconds.
    # It plays a beep for 0.25 seconds
    # and can be awaited by other asynchronous methods.
    async def beep(self):
        #print('about to beep') #for debugging
        self.buzzer.duty_u16(1000)
        await asyncio.sleep(0.25)
        self.buzzer.duty_u16(0)

    # This method runs asynchronously forever.
    # If self.running is True, it handles the button, neopixel, and buzzer.
    # If self.running is False, it turns off the neopixel and buzzer.
    # It awaits self.beep
    async def cycle_neopixel(self):
        while True:
            if self.running:
                self.neopixel[0] = self.colors[self.current_color_index]
                self.neopixel.write()
                if self.button.value() == 0: # This means the button is pressed
                    self.current_color_index = (self.current_color_index + 1) % len(self.colors)
                    await self.beep()
                else:
                    pass
            else:
                self.neopixel[0] = (0, 0, 0)
                self.neopixel.write()
                self.buzzer.duty_u16(0)
            await asyncio.sleep(threadsleep)

    # This method runs asynchronously forever.
    # It is subscribed to the 'ME35-24/aengus' channel
    # and it toggles self.running if 'start' or 'stop' is received.
    async def mqtt_subscribe(self):
        mqtt_broker = 'broker.hivemq.com' 
        port = 1883
        topic = 'ME35-24/best_nightlight'

        def callback(topic, msg):
            topic, msg = topic.decode(), msg.decode()
            print(topic, msg)
            if msg == 'start':
                #print("the message was 'start'") #for debugging
                self.running = True
            elif msg == 'stop':
                #print("the message was 'stop'") #for debugging
                self.running = False

        client = MQTTClient('ME35_chris', mqtt_broker, port, keepalive=60)
        client.set_callback(callback)
        client.connect()
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            await asyncio.sleep(threadsleep)


# The main code adds all four asynchronous forever functions
# to the event loop and then runs the event loop forever.
if True:
    nl = NightLightAsync()

    thread = asyncio.get_event_loop()

    #thread.create_task(nl.test()) #for testing purposes only
    thread.create_task(nl.breathe('GPIO0'))
    thread.create_task(nl.cycle_neopixel())
    thread.create_task(nl.mqtt_subscribe())

    thread.run_forever()

