import asyncio
import neopixel
from machine import Pin, PWM
import time
from networking import Networking

class Wizard:
    def __init__(self):
        self.buzzer = Pin(0, Pin.OUT)
        self.hit = 0
        self.msg = ''
        self.beginGame = False
        #Initialise ESPNOW
        self.networking = Networking()
        self.recipient_mac = b'\xFF\xFF\xFF\xFF\xFF\xFF'
        self.totalGametime = 300
        self.pressed = False
        self.counter = 0
        self.scorched = False
        self.lossed = False
        
        

    '''
    Handler function for ESPNOW. Extracts message and stores it in class variable
    '''
    def receive(self):
        # print("Receive")
        for mac, message, rtime in self.networking.aen.return_messages(): #You can directly iterate over the function
            self.msg = message

    def beep(self, frequency, duration):
        # Generate a tone using PWM
        pwm = PWM(self.buzzer)
        pwm.freq(frequency)  # Set the frequency in Hz
        pwm.duty(512)  # Set the duty cycle (50% for a constant tone)
        time.sleep(duration)  # Wait for the specified duration
        pwm.duty(0)  # Turn off the PWM signal to stop the sound
    
    '''
    Function to handle Wizard health. Each wizard has 1 life. If they are hit
    once they will "die" and not be in the game anymore. Hits are determined based
    on proximity to the Dragon.
    '''
    async def check_health(self):
        while True:
            # Read from ESPNOW
            self.networking.aen.irq(self.receive())
            placeholder = self.networking.aen.rssi()

            try:
                # rssi_value = placeholder[b'T2\x043H\x14'][0] #Cory ESP As Dragon
                rssi_value = placeholder[b'T2\x04!a\x9c'][0] #Jaylen ESP As Dragon
                print(rssi_value)
            except KeyError:
                pass

            if self.msg == '!scorched':
                self.scorched = True

            if self.msg == '!reset':
                self.msg = ''
                self.hit = 0
                self.counter = 0
                self.totalGametime = 300
                self.beginGame = True
                self.scorched = False
                self.lossed = False
                print("Game has started")
                self.beep(1000, 2)
            # if message is detected AND rssi is within the threashold, player gets hit
            if self.msg == '!breathingFire' and rssi_value > -75 and self.beginGame:

                print("HITTTT!")
                self.hit = 1
                

            # magic button has been found and being pressed for the first time
            # The wizards will send the same message to ensure every player in the game 
            # knows that the magic button was pressed.
            if self.msg == '!magic' and self.beginGame and not self.pressed:
                self.hit = 0
                self.counter = 0
                self.pressed = True
                self.networking.aen.send(self.recipient_mac, '!magic')
                self.beep(1000, .5)
                self.beep(1000, .5)
                print("The magic button has been found")

            # If a player is dead, advertise their ID, if not, put them in jail
            if self.hit == 1 and self.beginGame == True and self.counter < 3:
                message =  f'im dead'
                self.networking.aen.send(self.recipient_mac, message)
                print(f'Wizard Is Dead')
                self.beep(300, .5)
                # self.beep(300, .5)
                # self.beep(300, .5)
                self.counter = self.counter + 1 
            elif self.hit == 0 and self.beginGame == True:
                print(f'Wizard Is Alive')

            await asyncio.sleep(0.1)
            
    
    async def gameOver(self):
        while True:
            if self.totalGametime == 0:
                # self.led[0] = RED #Wizards outlasted the timer
                self.beep(1000, 2)
                self.inGame = False
                print("The Wizards Wins!")
            elif self.scorched and not self.lossed:
                self.beep(1000, 2)
                self.lossed = True
                print("The Dragon Wins")
            await asyncio.sleep(0.01)


    async def timer(self):
        #Timer decrementing till 5 minutes has gone by
        while True:
            if self.totalGametime > 0 and self.beginGame:
                minutes, seconds = divmod(self.totalGametime, 60)
                print(f"Time remaining: {minutes:02d}:{seconds:02d}", end='\r')
                self.totalGametime -= 1
                await asyncio.sleep(1)
            await asyncio.sleep(0.01)

    async def main(self):
        asyncio.create_task(self.check_health())
        asyncio.create_task(self.timer())
        asyncio.create_task(self.gameOver())
        while True:
            await asyncio.sleep(0.1)

wizard = Wizard()
asyncio.run(wizard.main())
