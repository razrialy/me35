import asyncio, neopixel, time
from machine import Pin, PWM
import machine
import sys
import time
from networking import Networking

class Dragon:
    def __init__(self, playerCount = 3):
        self.button = Pin(18, Pin.IN, Pin.PULL_UP)
        self.buzzer = Pin(0, Pin.OUT)

        self.cooldown = 0
        self.totalGametime = 300 #5 minute timer
        self.playerCount = playerCount
        self.scorched = False #Boolean when all wizards have been scorched
        self.wizards = {
        }
        #Booleans that say if the game is on and if game is being played together or individually
        self.inGame = False
        self.together = False
        self.individual = False
        self.magic = False
        self.counter = 0
        #Initialise ESPNOW
        self.msg = ''
        self.incomingMac = b'\x00\x00\x00\x00\x00\x00'
        self.networking = Networking()
        self.recipient_mac = b'\xFF\xFF\xFF\xFF\xFF\xFF' #This mac sends to all
    
    def receive(self):
        # print("Receive")
        for mac, message, rtime in self.networking.aen.return_messages(): #You can directly iterate over the function
            self.incomingMac = mac
            self.msg = message

    def beep(self, frequency, duration):
        # Generate a tone using PWM
        pwm = PWM(self.buzzer)
        pwm.freq(frequency)  # Set the frequency in Hz
        pwm.duty(512)  # Set the duty cycle (50% for a constant tone)
        time.sleep(duration)  # Wait for the specified duration
        pwm.duty(0)  # Turn off the PWM signal to stop the sound

    async def listen_ID(self):
        while True:

            
            ##################### GAME LOGIC #####################
            # Receive Wizard Macs Address
            self.networking.aen._irq(self.receive())

            if self.scorched:
                continue

            if self.msg == '!magic' and not self.magic:
                self.inGame = True
                self.scorched = False
                # Set cooldown to false because they have found the button before the dragon could complete the puzzle 
                self.cooldown = 0
                self.wizards = {
                }
                self.msg = ''
                self.incomingMac = b'\x00\x00\x00\x00\x00\x00'
                self.beep(1000, .5)
                self.beep(1000, .5)
                print("The wizards have found the magic button")
                self.magic = True


                # If reset, set all values back to 0
            if self.msg == '!reset':
                self.inGame = True
                self.scorched = False
                self.magic = False
                self.cooldown = 0
                self.totalGametime = 300 #5 minute timer 
                self.wizards = {
                }
                self.msg = ''
                self.incomingMac = b'\x00\x00\x00\x00\x00\x00'
                self.counter = 0
                self.beep(1000, 2)
                print("Resetting the game")


             #Spinner set game to individal
            if self.msg == '!individual':
                self.individual = True
                print("individual mode")

            #Spinner set game to together 
            if self.msg == '!together':
                self.together = True
                print("together mode")

            if self.msg == '!completed' and self.together:
                self.cooldown = 0
                self.beep(1000, 1)
                print("completed")

            if self.inGame:            
                # Need to add the Mac address of the wizard magic button to prevent game being over to soon
                if self.incomingMac != None and self.incomingMac != b'd\xe83\x874\x1c' and self.incomingMac != b'\x8c\xbf\xea\xcb\xa6`' and self.incomingMac != b'\x8c\xbf\xea\xcb\xa1\xc8' and self.incomingMac != b'T2\x04!v\xdc' and self.incomingMac != b'T2\x04![X':
                    print("Adding Wizard Mac To Dictionary")
                    self.wizards[self.incomingMac] = 1
                print(f'Number of Wizards: {len(self.wizards)}    Cooldown: {self.cooldown}')
                # Check if all wizards are hit
                if len(self.wizards) == self.playerCount:
                    print("All Wizards Scorched!")
                    self.scorched = True
            ######################################################

            await asyncio.sleep(0.1)

    async def breath_fire(self):
        prevButton = 1
        message = '!breathingFire'
        while True:
            if self.inGame:
                # Conditional to Breath Fire if button is pressed and not on cooldown
                #print("Button not pressed")
                if self.button.value() == 1 and not prevButton and not self.cooldown:
                    self.networking.aen.send(self.recipient_mac, message)
                    print("DragonBreath Sent to Wizard")
                    self.beep(250, .5)
                    self.beep(250, .5)
                    self.beep(250, .5)
                    self.beep(250, .5)
                    self.cooldown = 1
                prevButton = self.button.value()
            await asyncio.sleep(0.05)

    async def manage_fire(self):
        while True:
            # Begin 15 second cooldown
            if self.cooldown and self.inGame and self.individual:
                print("Dragon Cooling Down")
                #changed cooldown to be less 
                await asyncio.sleep(5) 
                print("Cooldown Finished")
                self.beep(1000, 1)
                self.cooldown = 0
            await asyncio.sleep(0.01)

    
    async def timer(self):
        #Timer decrementing till 5 minutes has gone by
        while True:
            if self.totalGametime > 0 and self.inGame:
                minutes, seconds = divmod(self.totalGametime, 60)
                print(f"Time remaining: {minutes:02d}:{seconds:02d}", end='\r')
                self.totalGametime -= 1
                await asyncio.sleep(1)
            await asyncio.sleep(0.01)

    async def gameOver(self):
        while True:
            if self.scorched and self.counter < 3:
                self.networking.aen.send(self.recipient_mac, '!scorched')
                self.beep(1000, 2)
                self.inGame = False
                print("The Dragon wins!")
                

            elif self.totalGametime == 0:
                self.inGame = False
                self.beep(1000, 2)
                print("The Wizards wins!")
                self.totalGametime = 1000000
            await asyncio.sleep(0.01)
                


    async def main(self):
        
        asyncio.create_task(self.breath_fire())
        asyncio.create_task(self.manage_fire())
        asyncio.create_task(self.listen_ID())
        asyncio.create_task(self.timer())
        asyncio.create_task(self.gameOver())

        while True:
            # print(f'In the Game: {self.inGame}    ', end='\r')
            await asyncio.sleep(0.01)

dragon = Dragon(playerCount = 3)
asyncio.run(dragon.main())
