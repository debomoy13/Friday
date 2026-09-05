import os
import yaml

def load_config(config_path="config.yaml"):
    """
    Loads configuration parameters from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        dict: A dictionary containing configuration parameters.
    """
    if not os.path.exists(config_path):
        # Fallback in case of running from inside src/
        parent_config = os.path.join("..", config_path)
        if os.path.exists(parent_config):
            config_path = parent_config
        else:
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
            
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    return config
