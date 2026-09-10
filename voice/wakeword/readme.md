# Wake Word Listener listener.py

This module handles the **wake word detection system** for the voice assistant.

The assistant continuously listens to the microphone in a lightweight mode and waits for the configured wake phrase.

Example:

> "Hey Jarvis"

Once the wake word is detected, the listener triggers the next stage of the voice assistant.

---

## How It Works

The wake word pipeline works as follows:

```text
Microphone
    ↓
Continuous Audio Stream
    ↓
openWakeWord Model
    ↓
Wake Word Detection
    ↓
Trigger Assistant




---

# 📄 `voice/README.md`

Since `recorder.py` is directly inside your `voice` folder, I would document it here rather than creating a random README just for one Python file.

```md
# Voice System

This directory contains the core voice input system for the assistant.

The voice system handles the journey from hearing the wake phrase to capturing the user's spoken command.

---

## Architecture

```text
Microphone
    │
    ▼
Wake Word Detection
    │
    │ "Hey Jarvis"
    ▼
Assistant Activated
    │
    ▼
Voice Recorder
    │
    ▼
Voice Activity Detection
    │
    ▼
Speech-to-Text