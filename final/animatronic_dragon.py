from machine import Pin, UART, PWM
import time, random, servo
from networking import Networking

class Puppet:
    def __init__(self):

        self.final_msg = b''

        self.networking = Networking()

        self.movements = [b'!up', b'!right', b'!left', b'!down']

        # set up servos
        self.head = PWM(Pin(2))
        self.head.freq(50)

        self.tail = PWM(Pin(6))
        self.tail.freq(50)

        self.wings = PWM(Pin(4))
        self.wings.freq(50)

        self.back_leg = PWM(Pin(5))
        self.back_leg.freq(50)

        self.front_leg = PWM(Pin(3))
        self.front_leg.freq(50)

        # set up LEDs
        self.led1 = Pin(8, Pin.OUT)
        self.led2 = Pin(9, Pin.OUT)
        self.led3 = Pin(10, Pin.OUT)

        self.led1.off()
        self.led2.off()
        self.led3.off()

        self.sequence = []

        self.one_done = False
        self.two_done = False

        self.mini_motor = servo.Servo(Pin(21))
        self.mini_motor.write_angle(20)

        self.button = Pin(20, Pin.IN, Pin.PULL_UP)

        self.is_solved = False

    def set_servo_angle(self, angle, motor):
        # Map angle to duty cycle range (adjust if necessary for your servo)
        min_duty = 1024  # Replace with your servo's minimum duty cycle
        max_duty = 8192  # Replace with your servo's maximum duty cycle
        duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
        motor.duty_u16(duty)

    def receive(self):
        print("Receive")
        for mac, message, rtime in self.networking.aen.return_messages(): #You can directly iterate over the function
            if message == None:
                self.final_msg = b''
            else:
                self.final_msg = message

    def movement(self, msg):
        print(type(msg))
        print(msg)
        if msg == b'!up':
            self.set_servo_angle(80, self.head)
            time.sleep(1)
            self.set_servo_angle(160, self.head)
            time.sleep(1)
            self.set_servo_angle(120, self.head)
            print("head moves")

        elif msg == b'!left':
            self.set_servo_angle(30, self.front_leg)
            #self.set_servo_angle(20, self.back_leg)
            time.sleep(1)
            self.set_servo_angle(120, self.front_leg)
            #self.set_servo_angle(70, self.back_leg)
            time.sleep(1)
            self.set_servo_angle(90, self.front_leg)
            #self.set_servo_angle(20, self.back_leg)
            print("legs move")

        elif msg == b'!right':
            self.set_servo_angle(120, self.wings)
            time.sleep(1)
            self.set_servo_angle(115, self.wings)
            time.sleep(1)
            self.set_servo_angle(120, self.wings)
            print("wings move")

        elif msg == b'!down':
            self.set_servo_angle(110, self.tail)
            time.sleep(1)
            self.set_servo_angle(80, self.tail)
            time.sleep(1)
            self.set_servo_angle(100, self.tail)
            print("tail moves")

        else:
            print("unknown message")

    def puzzle(self, msg):
        if msg == self.sequence[0] and not self.one_done and not self.two_done:
            self.movement(msg)
            self.one_done = True
            self.led1.on()
            self.mini_motor.write_angle(55)
        elif not self.one_done and not self.two_done:
            print("wrong movement - 1")

        if msg == self.sequence[1] and self.one_done:
            self.movement(msg)
            self.two_done = True
            self.led2.on()
            self.mini_motor.write_angle(90)
        elif self.one_done:
            print("wrong movement - 2")

        if msg == self.sequence[2] and self.one_done and self.two_done:
            self.movement(msg)
            self.led3.on()
            self.mini_motor.write_angle(125)
            self.networking.aen.send(b'\xff\xff\xff\xff\xff\xff', "!completed")
            self.is_solved = True
        elif self.one_done and self.two_done:
            print("wrong movement - 3")

    def randomize(self):
        self.sequence = []
        self.one_done = False
        self.two_done = False
        self.led1.off()
        self.led2.off()
        self.led3.off()

        while len(self.sequence) < 3:
            choice = random.choice(self.movements)  # Pick a random element
            if choice not in self.sequence:  # Avoid duplicates
                self.sequence.append(choice)

        print(self.sequence)

        self.movement(self.sequence[0])
        time.sleep(1)
        self.movement(self.sequence[1])
        time.sleep(1)
        self.movement(self.sequence[2])
        time.sleep(1)

    def run(self):
        if not self.button.value():
            print("Button pressed, resetting")
            self.randomize()
            self.is_solved = False

            while not self.is_solved:
                self.networking.aen._irq(self.receive())
                time.sleep(0.1)
                self.puzzle(self.final_msg)

puppet = Puppet()

while True:
    puppet.run()
