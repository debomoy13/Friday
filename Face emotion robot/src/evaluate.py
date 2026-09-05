import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
from src.dataset import get_dataloaders
from src.model import EmotionCNN
from src.utils import get_device

def evaluate_model(config, logger):
    """
    Loads the trained model weights and computes performance metrics on the test dataset split.
    
    Steps to implement:
    1. Retrieve the test dataloader.
    2. Instantiate the dynamic EmotionCNN model.
    3. Load the saved weights (state_dict) from the best model path.
    4. Move the model to the resolved device and set it to evaluation mode (`model.eval()`).
    5. Collect all predictions and true target labels from the test dataset.
    6. Compute the confusion matrix and classification report (using scikit-learn).
    7. Save the classification report text to the outputs folder (e.g., `outputs/classification_report.txt`).
    8. Plot the confusion matrix using Matplotlib and save the figure (e.g., `outputs/confusion_matrix.png`).
    9. Log summary scores to the console.
    
    Args:
        config (dict): Config dictionary.
        logger (logging.Logger): Logging engine.
    """
    logger.info("Initializing model evaluation on test dataset...")
    # TODO: Implement predictions logging, metrics evaluation, confusion matrix visualization, 
    # and file outputs generation.
    raise NotImplementedError("Implement evaluate_model in src/evaluate.py")
