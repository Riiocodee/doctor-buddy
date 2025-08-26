import pyttsx3
engine = pyttsx3.init()
voice=engine.getProperty('voices')[1]
engine.setProperty('voice',voice.id)
engine.setProperty('rate', 120)  # Adjust this value for slower speech
engine.say("hello riya how are you ")
engine.runAndWait()

