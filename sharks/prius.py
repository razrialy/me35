from machine import Pin, PWM, I2C
from mqtt import MQTTClient
import time, mqtt

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

def buzzer(frequency=440, duration=1):
    buzzer_pwm = PWM(Pin(18, Pin.OUT))  # GPIO18 pin
    buzzer_pwm.freq(frequency)
    buzzer_pwm.duty_u16(1000)
    time.sleep(duration)
    buzzer_pwm.duty_u16(0)
    
    buzzer_pwm.deinit()
        
class CarRight: 
    def __init__(self):
        # Motor setup
        self.right1 = PWM(Pin('GPIO14', Pin.OUT)) # will be in different class eventually
        self.right1.freq(100)
        self.right2 = PWM(Pin('GPIO15', Pin.OUT))
        self.right2.freq(100)
        self.right2.duty_u16(0)
        self.right1.duty_u16(0)
        
        self.status = False
        self.mqtt_sub_R()

    def backward_R(self, duty):
        self.right1.duty_u16(duty)
        self.right2.duty_u16(0)
    
    def forward_R(self, duty):
        self.right1.duty_u16(0)
        self.right2.duty_u16(duty)
        
    def left_R(self, duty):
        self.right1.duty_u16(0)
        self.right2.duty_u16(20000)
    
    def right_R(self, duty):
        self.right1.duty_u16(0)
        self.right2.duty_u16(duty)
        
    def stop_R(self):
        self.right1.duty_u16(0)
        self.right2.duty_u16(0)
    
    def mqtt_sub_R(self):
        self.stop_R()
        mqtt_broker = 'broker.hivemq.com' 
        port = 1883
        topic = 'ME35-24/prius5'       # this reads anything sent to ME35
        #topic_pub = 'ME35-24/prius5'
        
        def callback(topic, msg):
            topic, msg = topic.decode(), msg.decode()
            print(topic, msg)
            
            if msg == "start":
                self.status = True
                buzzer()
            elif msg == "stop":
                buzzer()
                self.stop_R()
                self.status = False
            
            if self.status == True and msg != "start":
                split = msg.split(",")
        
                split[1] = float(split[1])
                
                dist = abs(split[1])
                #print(dist)
                
                if dist <= 7:
                    du = 25000
                elif 7 < dist <= 12:
                    du = 45000
                elif 12 < dist:
                    du = 65000
                
                if split[0] == 'f':
                    self.forward_R(du) # go forward
                elif split[0] == 'b':
                    self.backward_R(du) # go backward
                elif split[0] == 'r':
                    self.right_R(du) # go right
                elif split[0] == 'l':
                    self.left_R(du) # go left
        
        client = MQTTClient('PriusR', mqtt_broker, port, keepalive=60)
        client.set_callback(callback)
        client.connect()
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            time.sleep(0.1)

class CarLeft: 
    def __init__(self):
        # Motor setup
        self.left1 = PWM(Pin('GPIO16', Pin.OUT))
        self.left1.freq(100)
        self.left2 = PWM(Pin('GPIO17', Pin.OUT))
        self.left2.freq(100)
        self.left2.duty_u16(0)
        self.left1.duty_u16(0)
        self.status = False
        self.mqtt_sub_L()
    
    def backward_L(self, duty):
        self.left1.duty_u16(duty)
        self.left2.duty_u16(0)
    
    def forward_L(self, duty):
        self.left1.duty_u16(0)
        self.left2.duty_u16(duty)
        
    def left_L(self, duty):
        self.left1.duty_u16(0)
        self.left2.duty_u16(duty)
    
    def right_L(self, duty):
        self.left1.duty_u16(0)
        self.left2.duty_u16(20000)
        
    def stop_L(self):
        self.left1.duty_u16(0)
        self.left2.duty_u16(0)
        
    def mqtt_sub_L(self):
        self.stop_L()
        mqtt_broker = 'broker.hivemq.com' 
        port = 1883
        topic = 'ME35-24/prius5'       # this reads anything sent to ME35
        #topic_pub = 'ME35-24/prius5'

        def callback(topic, msg):
            topic, msg = topic.decode(), msg.decode()
            print(topic, msg)
            
            if msg == "start":
                self.status = True
                buzzer()
            elif msg == "stop":
                buzzer()
                self.stop_L()
                self.status = False

            
            if self.status == True and msg != "start":
                split = msg.split(",")
        
                split[1] = float(split[1])
                
                dist = abs(split[1])
                print(dist)
                
                if dist <= 7:
                    du = 25000
                elif 7 < dist <= 12:
                    du = 45000
                elif 12 < dist:
                    du = 65000
                
                if split[0] == 'f':
                    self.forward_L(du) # go forward
                elif split[0] == 'b':
                    self.backward_L(du) # go backward
                elif split[0] == 'r':
                    self.right_L(du) # go right
                elif split[0] == 'l':
                    self.left_L(du) # go left
                

        client = MQTTClient('PriusL', mqtt_broker, port, keepalive=60)
        client.set_callback(callback)
        client.connect()
        client.subscribe(topic.encode())

        while True:
            client.check_msg()
            time.sleep(0.1)
