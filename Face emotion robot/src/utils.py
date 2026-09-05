import os
import cv2
import torch
import numpy as np

def get_device(device_setting="auto"):
    """
    Resolves and returns the torch.device object based on configuration and hardware availability.
    
    Args:
        device_setting (str): "cuda", "cpu", or "auto"
        
    Returns:
        torch.device: The resolved device (CPU or CUDA).
    """
    if device_setting == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    elif device_setting == "cpu":
        return torch.device("cpu")
    else:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_face_cascade(cascade_path="haarcascade_frontalface_default.xml"):
    """
    Loads OpenCV's Haar Cascade Face Detector.
    
    Args:
        cascade_path (str): Local path or filename of the XML cascade file.
        
    Returns:
        cv2.CascadeClassifier: The loaded classifier cascade.
        
    Note for developer:
        You can load the built-in OpenCV classifier using:
        `cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')`
    """
    # Try loading from the provided path
    if os.path.exists(cascade_path):
        cascade = cv2.CascadeClassifier(cascade_path)
    else:
        # Fallback to OpenCV built-in cascades folder
        builtin_path = os.path.join(cv2.data.haarcascades, os.path.basename(cascade_path))
        cascade = cv2.CascadeClassifier(builtin_path)
        
    if cascade.empty():
        # Final fallback using direct OpenCV build-in default
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    if cascade.empty():
        raise FileNotFoundError(f"Haar cascade face detector could not be loaded from path: {cascade_path}")
        
    return cascade

def preprocess_face(face_img, target_size=(64, 64), channels=1):
    """
    Preprocesses a cropped face image (numpy array) to be fed into the PyTorch CNN model.
    
    Expected logic:
    1. Convert to grayscale if channels == 1 and face_img is BGR (color).
    2. Resize to target_size (e.g., 64x64).
    3. Normalize pixel values (e.g., scaling to [0, 1] by dividing by 255.0).
    4. Reshape dimensions to match PyTorch expectations: (Channels, Height, Width).
    5. Convert to torch.Tensor.
    
    Args:
        face_img (numpy.ndarray): Cropped face image.
        target_size (tuple): Target (height, width) dimensions.
        channels (int): Channel count (1 for grayscale, 3 for RGB).
        
    Returns:
        torch.Tensor: Preprocessed image tensor ready for inference.
    """
    # TODO: Implement face preprocessing steps
    raise NotImplementedError("Implement preprocess_face in src/utils.py")
