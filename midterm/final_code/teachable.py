from pyscript.js_modules import teach, pose, ble_library, mqtt_library

# ble = ble_library.newBLE()
myClient = mqtt_library.myClient("broker.hivemq.com", 8884)
mqtt_connected = False
pub_topic = 'ME35-24/mermaid'

async def received_mqtt_msg(message):
    message = myClient.read().split('	')  # Add here anything you want to do with received messages

async def run_model(URL2):
    s = teach.s  # or s = pose.s
    s.URL2 = URL2
    await s.init()

async def connect(name):
    global mqtt_connected
    myClient.init()
    while not myClient.connected:
        await asyncio.sleep(2)
    #myClient.subscribe(sub_topic)
    myClient.callback = received_mqtt_msg
    mqtt_connected = True
    # if await ble.ask(name):
    #     print('name ', name)
    #     await ble.connect()
    #     print('connected!')

async def disconnect():
    # await ble.disconnect()
    print('disconnected')

def send(message):
    print('sending ', message)
    myClient.publish(pub_topic, message)
    # ble.write(message)

def get_predictions(num_classes):
    predictions = []
    for i in range(num_classes):
        divElement = document.getElementById('class' + str(i))
        if divElement:
            divValue = float(divElement.innerHTML.split(':')[1].strip())  # Convert to float for comparison
            predictions.append(divValue)
    return predictions

def get_class_name(index):
    # Modify this to match your class names
    class_names = ['loud', 'quiet', 'note', 'song', 'none']
    return class_names[index]

import asyncio
await run_model("https://teachablemachine.withgoogle.com/models/PZmXA32XM/")  # Change to your model link
await connect('Rachael')

while True:
    if mqtt_connected:
        predictions = get_predictions(5)  # Get predictions for 5 classes
        for i in range(4):  # Check only the first 4 classes
            if predictions[i] > 80:  # Send message if confidence is above 80%
                class_name = get_class_name(i)
                print(class_name)
                send(class_name)
                break
        # Do nothing if the last class (index 4) is detected
    await asyncio.sleep(2)

