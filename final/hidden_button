from Final_Project.Final.networking import Networking
from machine import Pin
import time

class Magic:

    def __init__(self):
        #Initialise
        self.networking = Networking()
        self.button = Pin(0, Pin.IN, Pin.PULL_UP)
        self.recipient_mac = b'\xff\xff\xff\xff\xff\xff' #This mac sends to all
        self.message = '!magic'
        self.pressed = False
        self.msg = ''

    def receive(self):
        for mac, message, rtime in self.networking.aen.return_messages(): 
            self.msg = message
        
    def play(self):
        while True:
            self.receive()
            if self.button.value() == 1 and not self.pressed:  # Button pressed (LOW)
                print("Button is not pressed")
            elif self.button.value() == 0 and not self.pressed:  # Button not pressed (HIGH)
                print("Button is pressed")
                self.networking.aen.send(self.recipient_mac, self.message)
                self.pressed = True
            time.sleep(0.1)
            if self.msg == '!reset':
              self.pressed = False
            

magic = Magic()

while True:
    magic.play()
