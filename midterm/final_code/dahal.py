import time
import asyncio
from machine import Pin, SoftI2C, ADC
import ssd1306
import network
from mqtt import MQTTClient

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('Tufts_Robot', '')

while wlan.ifconfig()[0] == '0.0.0.0':
    print('.', end=' ')
    time.sleep(1)

# We should have a valid IP now via DHCP
print(wlan.ifconfig())

class Dahal:
    def __init__(self):
        self.i2c = SoftI2C(scl=Pin(7), sda=Pin(6))
        self.screen = ssd1306.SSD1306_I2C(128, 64, self.i2c)

        self.pot = ADC(Pin(3))
        self.pot.atten(ADC.ATTN_11DB)

        self.sd = Pin(9, Pin.IN)
        
        # MQTT setup
        self.mqtt_broker = 'broker.emqx.io'
        self.port = 1883
        self.topic_pub = 'ME35-24/mermaid'
        
        self.client = MQTTClient('rach_dahal', self.mqtt_broker, self.port, keepalive=60)
        self.client.connect()
        print('Connected to %s MQTT broker' % (self.mqtt_broker))

    def draw_line(self, x0, y0, x1, y1, color):
        """Draws a line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.screen.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            err2 = err * 2
            if err2 > -dy:
                err -= dy
                x0 += sx
            if err2 < dx:
                err += dx
                y0 += sy

    def draw_circle(self, x, y, radius, color):
        """Draws a circle using the midpoint circle algorithm."""
        f = 1 - radius
        ddF_x = 1
        ddF_y = -2 * radius
        x_pos = 0
        y_pos = radius

        self.screen.pixel(x, y + radius, color)
        self.screen.pixel(x, y - radius, color)
        self.screen.pixel(x + radius, y, color)
        self.screen.pixel(x - radius, y, color)

        while x_pos < y_pos:
            if f >= 0:
                y_pos -= 1
                ddF_y += 2
                f += ddF_y
            x_pos += 1
            ddF_x += 2
            f += ddF_x

            self.screen.pixel(x + x_pos, y + y_pos, color)
            self.screen.pixel(x - x_pos, y + y_pos, color)
            self.screen.pixel(x + x_pos, y - y_pos, color)
            self.screen.pixel(x - x_pos, y - y_pos, color)
            self.screen.pixel(x + y_pos, y + x_pos, color)
            self.screen.pixel(x - y_pos, y + x_pos, color)
            self.screen.pixel(x + y_pos, y - x_pos, color)
            self.screen.pixel(x - y_pos, y - x_pos, color)

    def draw(self):
        # Clear the display
        self.screen.fill(0)

        # Draw smaller fish head (circle) at (95, 32) with radius 5
        self.draw_circle(95, 32, 5, 1)  # Head at (95, 32) with radius 5

        # Draw smaller fish tail (triangle using lines)
        self.draw_line(100, 32, 110, 27, 1)  # Left side of tail
        self.draw_line(100, 32, 110, 37, 1)  # Right side of tail
        self.draw_line(110, 27, 110, 37, 1)  # Base of tail

        # Draw mirrored fish on the left
        self.draw_circle(33, 32, 5, 1)  # Head at (33, 32) with radius 5
        # Adjusted tail coordinates to point away from the head
        self.draw_line(28, 32, 18, 37, 1)  # Left side of tail (flipped)
        self.draw_line(28, 32, 18, 27, 1)  # Right side of tail (flipped)
        self.draw_line(18, 27, 18, 37, 1)  # Base of tail

        self.screen.text('Welcome', 37, 0, 1)  # to display text
        self.screen.text('to', 55, 15, 1)  # to display text
        self.screen.text('the', 52, 30, 1)  # to display text
        self.screen.text('sea!', 50, 45, 1)  # to display text

        self.screen.show()  # Update the display

    def get_note_from_pot(self, pot_value):
        """Assign notes based on potentiometer value."""
        note_ranges = [
            (0, 585),    # C
            (586, 1170), # D
            (1171, 1755),# E
            (1756, 2340),# F
            (2341, 2925),# G
            (2926, 3510),# A
            (3511, 4095) # B
        ]
        
        for i, (low, high) in enumerate(note_ranges):
            if low <= pot_value <= high:
                return ["C", "D", "E", "F", "G", "A", "B"][i]
        return None

    async def monitor_button(self):
        while True:
            # Check if button is pressed
            if not self.sd.value():  # Assuming low means pressed
                pot_value = self.pot.read()  # Read the potentiometer
                note = self.get_note_from_pot(pot_value)  # Get the corresponding note
                
                if note:
                    print(f"Potentiometer Value: {pot_value}, Note: {note}")  # Print value and note
                    self.client.publish(self.topic_pub.encode(), note.encode())  # Publish note via MQTT
                    
            await asyncio.sleep(0.1)  # Add a small delay to debounce the button

    async def run(self):
        while True:
            self.draw()  # Draw the fish on the screen
            await asyncio.sleep(0.1)  # Refresh rate

# Main execution
dahal = Dahal()

async def main():
    await asyncio.gather(dahal.run(), dahal.monitor_button())

asyncio.run(main())
