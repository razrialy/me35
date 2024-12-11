from networking import Networking
from machine import Pin, SoftI2C, ADC, PWM
import asyncio
from lsm6ds3 import LSM6DS3
from button import Button

class Spell:
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    OTHER = "other"

class Wand:
    def __init__(self):
        self.tag_state = False     # whether tagged
        self.msg = ""

        # Initialize I2C
        self.i2c = SoftI2C(scl=Pin(23), sda=Pin(22)) # 23 -> Pin 5; 22 -> Pin 4
        self.lsm = LSM6DS3(self.i2c)

        self.button = Button(pin_num=0)

        # Networking
        self.networking = Networking()

    def my_callback(self):
        for mac, message, rtime in self.networking.aen.return_messages(): #You can directly iterate over the function
            self.msg = message

    def read_movement_data(self):
        ax, ay, az, gx, gy, gz = self.lsm.get_readings()
        return gy, gx # TODO adjust the axis of rotation

    def determine_spell(self, lr_data, ud_data):
        THRESHOLD = 32764 # TODO tune treshold

        counts = {
            Spell.UP: (sum(1 for value in ud_data if value >= THRESHOLD), abs(max(ud_data, default=0))),
            Spell.DOWN: (sum(1 for value in ud_data if value <= -THRESHOLD), abs(min(ud_data, default=0))),
            Spell.LEFT: (sum(1 for value in lr_data if value >= THRESHOLD), abs(max(lr_data, default=0))),
            Spell.RIGHT: (sum(1 for value in lr_data if value <= -THRESHOLD), abs(min(lr_data, default=0)))
        }

        max_spell, (max_count, _) = max(counts.items(), key=lambda x: x[1][0])
        max_weak_spell, (_, max_weak_val) = max(counts.items(), key=lambda x: x[1][1])
        if max_count == 0:
            print(max_weak_val)
        return max_spell if max_count > 0 else (max_weak_spell if max_weak_val > 10 else Spell.OTHER)

    async def puzzle(self):
        if self.button.is_pressed():
            lr_data = []
            ud_data = []
            while self.button.is_being_pressed():
                await asyncio.sleep_ms(10)
                gz, gx = self.read_movement_data()
                lr_data.append(gz)
                ud_data.append(gx)

            movement = self.determine_spell(lr_data, ud_data)

            if movement == Spell.OTHER:
                print("other spell")
            else:
                print(movement)
                self.networking.aen.send(b'\xFF\xFF\xFF\xFF\xFF\xFF', b'!' + movement)
                await asyncio.sleep_ms(10)  # TODO Tune the cooldown as needed

    async def run(self):
        while True:
            self.my_callback()
            await asyncio.gather(
                self.puzzle(),
            )

# Initialize the Wand object and run the tasks asynchronously
wand = Wand()
asyncio.run(wand.run())
