# Copyright 2022 David Scripka. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# This file is copied from wakeword repo.
# Imports
import argparse
import numpy as np
import pyaudio
from openwakeword.model import Model
import openwakeword.utils


def jarvis_awake():
    print("\nHey Debomoy, what's up!")


def main():
    # Parse input arguments
    parser = argparse.ArgumentParser(description="Wake word listener using openWakeWord")
    parser.add_argument(
        "--wakeword",
        help="The specific wake word model to detect (default: 'hey_jarvis', use 'all' for all models)",
        type=str,
        default="hey_jarvis",
        required=False,
    )
    parser.add_argument(
        "--threshold",
        help="Confidence score threshold for wake word detection (0.0 to 1.0)",
        type=float,
        default=0.5,
        required=False,
    )
    parser.add_argument(
        "--chunk_size",
        help="How much audio (in number of samples) to predict on at once",
        type=int,
        default=1280,
        required=False,
    )
    parser.add_argument(
        "--model_path",
        help="The path of a specific custom model file to load",
        type=str,
        default="",
        required=False,
    )
    parser.add_argument(
        "--inference_framework",
        help="The inference framework to use (either 'onnx' or 'tflite')",
        type=str,
        default="onnx",
        required=False,
    )

    args = parser.parse_args()

    # Determine which model(s) to load
    def load_model():
        if args.model_path != "":
            return Model(wakeword_models=[args.model_path], inference_framework=args.inference_framework)
        elif args.wakeword.lower() == "all":
            return Model(inference_framework=args.inference_framework)
        else:
            return Model(wakeword_models=[args.wakeword], inference_framework=args.inference_framework)

    try:
        owwModel = load_model()
    except Exception:
        print("Downloading missing openWakeWord default models...")
        openwakeword.utils.download_models()
        owwModel = load_model()

    n_models = len(owwModel.models.keys())
    active_models = list(owwModel.models.keys())

    # Get microphone stream
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = args.chunk_size
    audio_interface = pyaudio.PyAudio()
    mic_stream = audio_interface.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    # Run capture loop continuously, checking for wakewords
    # Generate output string header
    print("\n\n")
    print("#" * 100)
    print(f"Listening for wakeword: {', '.join(active_models)} (threshold={args.threshold})...")
    print("#" * 100)
    print("\n" * (n_models * 3))

    try:
        while True:
            # Get audio
            raw_audio = mic_stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(raw_audio, dtype=np.int16)

            # Feed to openWakeWord model
            owwModel.predict(audio_data)

            # Column titles
            n_spaces = 16
            output_string_header = """
            Model Name         | Score | Wakeword Status
            --------------------------------------
            """

            wakeword_triggered = False
            for mdl in owwModel.prediction_buffer.keys():
                # Add scores in formatted table
                scores = list(owwModel.prediction_buffer[mdl])
                curr_score = format(scores[-1], ".20f").replace("-", "")
                is_detected = scores[-1] > args.threshold

                output_string_header += f"""{mdl}{" "*(n_spaces - len(mdl))}   | {curr_score[0:5]} | {"Wakeword Detected!" if is_detected else "--"+" "*20}
            """
                if is_detected:
                    wakeword_triggered = True

            # Print results table
            print("\033[F" * (4 * n_models + 1))
            print(output_string_header, "                             ", end="\r")

            if wakeword_triggered:
                jarvis_awake()
                owwModel.reset()

    except KeyboardInterrupt:
        print("\nStopping listener...")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        audio_interface.terminate()


if __name__ == "__main__":
    main()

