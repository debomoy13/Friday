# 🎙️ Wake Word Detection

Real-time, lightweight wake word detection system for Friday/Jarvis powered by [openWakeWord](https://github.com/dscripka/openWakeWord) and ONNX Runtime.

The listener continuously monitors microphone audio in a low-resource loop and triggers assistant activation upon detecting configured wake phrases (default: **"Hey Jarvis"**).

---

## 🏗️ Architecture & Pipeline

```text
       🎤 Microphone (16kHz PCM Audio Stream)
                         │
                         ▼
             Audio Chunking (1280 samples)
                         │
                         ▼
             openWakeWord (ONNX Engine)
                         │
                         ▼
           Confidence Score Evaluation (≥ 0.5)
                         │
           ┌─────────────┴─────────────┐
           ▼                           ▼
  [Below Threshold]           [Wake Word Detected]
   Continue Stream                     │
                                       ├─► Trigger jarvis_awake()
                                       └─► Reset Prediction Buffer
```

---

## ✨ Features

- **⚡ Real-time & Low Latency**: Fast inference using ONNX Runtime for instant keyword spotting.
- **🎯 Targeted Filtering**: Configured to listen specifically for `"hey_jarvis"`, minimizing false triggers.
- **🛡️ Duplicate Trigger Prevention**: Automatically resets internal feature buffers upon activation to avoid multi-triggering on trailing speech.
- **🔄 Auto-Model Management**: Automatically downloads missing pre-trained wake word models on first launch.
- **🎤 Robust Stream Handling**: Handles audio input overflow gracefully and ensures clean microphone teardown on exit.

---

## 📁 Directory Layout

```text
voice/wakeword/
├── listener.py       # Real-time microphone capture & wake word inference loop
├── recorder.py       # Voice capture module for speech-to-text recording
└── README.md         # Module documentation
```

---

## 🚀 Getting Started

### 1. Install Dependencies

Ensure you have the required audio and ML libraries installed:

```bash
pip install -r ../requirements.txt
```

### 2. Run the Listener

Start listening for the default wake word (**"Hey Jarvis"**):

```bash
python listener.py
```

---

## ⚙️ CLI Options & Configuration

| Argument | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--wakeword` | `str` | `hey_jarvis` | Wake word to detect (`hey_jarvis`, `alexa`, `hey_mycroft`, or `all`). |
| `--threshold` | `float` | `0.5` | Confidence threshold for activation (between `0.0` and `1.0`). |
| `--chunk_size` | `int` | `1280` | Number of audio samples per prediction chunk (1280 samples = 80ms at 16kHz). |
| `--model_path` | `str` | `""` | Optional path to a custom `.onnx` or `.tflite` wake word model file. |
| `--inference_framework` | `str` | `onnx` | Backend runtime engine (`onnx` or `tflite`). |

### Examples

**Run with higher sensitivity threshold:**
```bash
python listener.py --threshold 0.65
```

**Listen for all supported wake words:**
```bash
python listener.py --wakeword all
```

**Load a custom trained model:**
```bash
python listener.py --model_path /path/to/custom_model.onnx
```

---

## 🧩 Programmatic Integration

You can import and trigger custom actions upon wake word detection from your main assistant pipeline:

```python
from voice.wakeword.listener import jarvis_awake, main

# Run the listener standalone or invoke from voice/main.py
if __name__ == "__main__":
    main()
```