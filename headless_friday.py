import os
import time
import json
import asyncio
import speech_recognition as sr
import pyttsx3
from core.orchestrator import FridayOrchestrator

# Initialize the local Windows Speech API (SAPI5) offline synthesis engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Select Zira or any female voice if available to fit the Friday persona
for voice in voices:
    if "zira" in voice.name.lower() or "female" in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break
engine.setProperty('rate', 170)  # Pacing speed

def speak(text):
    """Speaks text using system speaker and logs to standard outputs."""
    print(f"[Friday]: {text}")
    # Remove markdown tags before speech
    clean_text = text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
    engine.say(clean_text)
    engine.runAndWait()

# Initialize the Friday orchestrator
# This loads DB preferences (like provider = 'ollama', model = 'qwen3.6')
orchestrator = FridayOrchestrator()

# Initialize speech recognizer
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Configure threshold values
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 1.0

def calibrate_microphone():
    print("Calibrating microphone for ambient noise...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print("Calibration complete.")

async def process_voice_command(command: str, source):
    """Processes verbal requests, running tool execution chains and checking approvals."""
    user_name = orchestrator.brain.user_name
    print(f"Processing command: '{command}'")
    
    # Process user input via the orchestrator async generator
    async for update in orchestrator.process_user_input(command):
        utype = update["type"]
        
        if utype == "tool_executing":
            print(f"-> Running tool: {update['name']}")
            
        elif utype == "requires_approval":
            # Dangerous tool execution intercepted! Prompt user verbally for approval
            speak(f"Boss, I need authorization to run {update['tool_name']}. Please say approve or deny.")
            
            # Listen to mic for the voice authorization
            approved = False
            try:
                # Capture next phrase
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=4)
                response = recognizer.recognize_google(audio).lower()
                print(f"Auth response heard: '{response}'")
                
                if "approve" in response or "yes" in response or "authorize" in response or "ok" in response:
                    approved = True
            except Exception:
                approved = False  # Denied by default on noise/timeout
                
            if approved:
                speak("Authorization granted. Executing.")
                async for sub_update in orchestrator.execute_approved_action(update["request_id"]):
                    if sub_update["type"] == "final_response":
                        speak(sub_update["content"])
            else:
                speak("Execution denied. Cancelling action.")
                async for sub_update in orchestrator.deny_approved_action(update["request_id"]):
                    if sub_update["type"] == "final_response":
                        speak(sub_update["content"])
                        
        elif utype == "final_response":
            speak(update["content"])

async def main():
    user_name = orchestrator.brain.user_name
    assistant_name = orchestrator.brain.assistant_name.lower()
    
    calibrate_microphone()
    speak(f"Friday background systems operational. Monitoring active, {user_name}.")

    while True:
        with microphone as source:
            try:
                print("Listening for wake phrase...")
                # Stream audio with timeout to keep thread responsive
                audio = recognizer.listen(source, timeout=4, phrase_time_limit=6)
                phrase = recognizer.recognize_google(audio).lower()
                print(f"Heard: '{phrase}'")
                
                # Check if wake word triggered
                if assistant_name in phrase:
                    # Find any command spoken immediately after the wake word
                    idx = phrase.find(assistant_name)
                    command = phrase[idx + len(assistant_name):].strip()
                    
                    if not command:
                        # Wake word triggered alone, ask for instructions
                        speak(f"Yes, {user_name}?")
                        try:
                            audio_cmd = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                            command = recognizer.recognize_google(audio_cmd)
                        except Exception:
                            continue
                            
                    if command:
                        await process_voice_command(command, source)
                        
            except sr.WaitTimeoutError:
                # Loop timeout, keep listening
                continue
            except sr.UnknownValueError:
                # Intelligible speech check failed, ignore
                continue
            except Exception as e:
                print(f"Headless error: {str(e)}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Friday systems shutting down.")
