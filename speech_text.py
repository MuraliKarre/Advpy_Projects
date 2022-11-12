# Convert Speech to Text
# pip install SpeechRecognition
import speech_recognition as sr
import pyttsx3
import requests

def SpeechToText():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        said = ""

        try:
            said = r.recognize_google(audio)
            print(said)
        except Exception as e:
            print("Exception: " + str(e))

    return said


text = get_audio()

except sr.UnknownValueError:
    print("Sorry Can't understand, Try again")
    SpeechToText()