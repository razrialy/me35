import mido

# Open your MIDI file
midi_file = mido.MidiFile('C:\\Users\\Rachael Azrialy\\Downloads\\poor.mid')


# Create a list to store messages
midi_messages = []

# Parse the MIDI file and convert messages to a simpler format
for msg in midi_file:
    if msg.type in ['note_on', 'note_off']:
        midi_messages.append([msg.type, msg.note, msg.velocity, msg.time])

# Write this list to a Python file or a text file
with open("poor.py", "w") as f:
    f.write(f"midi_data = {midi_messages}")
