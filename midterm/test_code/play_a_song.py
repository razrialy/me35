import time
from BLE_CEEO import Yell
from poor_unfortuante import midi_data as poor  # Import the MIDI data from the file

# MIDI commands and settings
NoteOn = 0x90
NoteOff = 0x80
velocity = {'off': 0, 'ppp': 20, 'mp': 53, 'f': 80}  # Adjust velocity levels as needed

# Initialize BLE MIDI connection
p = Yell('Rachael', verbose=True, type='midi')
p.connect_up()

# Helper function to send MIDI messages
def send_midi(note, velocity, note_on=True):
    channel = 0
    command = NoteOn if note_on else NoteOff
    timestamp_ms = time.ticks_ms()
    tsM = (timestamp_ms >> 7 & 0b111111) | 0x80
    tsL = 0x80 | (timestamp_ms & 0b1111111)

    # Construct the MIDI message
    midi_message = bytes([tsM, tsL, command | channel, note, velocity])
    p.send(midi_message)

# Play the MIDI data
for event in poor:
    msg_type, note, velocity, duration = event
    if msg_type == 'note_on':
        send_midi(note, velocity, note_on=True)
    elif msg_type == 'note_off':
        send_midi(note, velocity, note_on=False)

    # Wait for the specified duration before the next event
    time.sleep(duration)

# Disconnect BLE after playback
p.disconnect()
