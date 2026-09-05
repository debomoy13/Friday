# Face Emotion Recognition

An end-to-end facial emotion recognition pipeline using PyTorch, OpenCV, and a modular architecture.

## 📁 Project Structure

```text
Face emotion robot/
├── config.yaml              # Central configuration file
├── requirements.txt         # Project dependencies
├── main.py                  # Main entry point / CLI orchestrator
├── README.md                # Project documentation
├── .gitignore               # Git ignore rules
│
├── data/
│   ├── raw/                 # Raw captured/collected facial emotion images
│   │   ├── angry/
│   │   ├── happy/
│   │   ├── neutral/
│   │   ├── sad/
│   │   └── surprise/
│   └── split/               # Partitioned train, val, and test datasets
│       ├── train/
│       │   ├── angry/
│       │   ├── happy/
│       │   ├── neutral/
│       │   ├── sad/
│       │   └── surprise/
│       ├── val/
│       │   ├── angry/
│       │   ├── happy/
│       │   ├── neutral/
│       │   ├── sad/
│       │   └── surprise/
│       └── test/
│           ├── angry/
│           ├── happy/
│           ├── neutral/
│           ├── sad/
│           └── surprise/
│
├── models/                  # Saved model checkpoints and weights (.pth)
├── outputs/                 # Evaluation plots, logs, and metrics
│
└── src/                     # Source code modules
    ├── __init__.py
    ├── config.py            # Configuration loader
    ├── data_collection.py   # Webcam automated face data collector
    ├── dataset_prep.py      # Dataset splitter and preprocessor
    ├── evaluate.py          # Model evaluation routines
    ├── logger.py            # Structured logging setup
    ├── model.py             # CNN model definitions
    ├── predict.py           # Real-time / batch emotion inference
    ├── train.py             # Model training loop
    └── utils.py             # General helper utilities
```

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Data Collection**:
   Capture training images for emotions via webcam:
   ```bash
   python main.py --mode collect --emotion happy
   ```

3. **Dataset Splitting**:
   Split raw images into `train`, `val`, and `test`:
   ```bash
   python main.py --mode split
   ```

4. **Training**:
   Train the emotion recognition model:
   ```bash
   python main.py --mode train
   ```

5. **Real-Time Inference**:
   Run live webcam emotion detection:
   ```bash
   python main.py --mode predict
   ```