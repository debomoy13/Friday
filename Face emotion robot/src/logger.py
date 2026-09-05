import os
import logging

def setup_logger(output_dir="outputs"):
    """
    Configures and returns a logger that outputs to both the console and a log file.
    
    Args:
        output_dir (str): Directory where the log file will be saved.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    os.makedirs(output_dir, exist_ok=True)
    log_filepath = os.path.join(output_dir, "app.log")
    
    logger = logging.getLogger("FaceEmotionApp")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handler registration if setup_logger is called multiple times
    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_filepath, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger
