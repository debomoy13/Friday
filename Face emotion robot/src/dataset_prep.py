from config import config
import os
import shutil
import random

def split_dataset(config, logger):
    """
    Splits the collected raw images from `data/raw/` into `data/split/train/`, `data/split/val/`, and `data/split/test/`.
    
    Steps to implement:
    1. Retrieve directories and split ratios from configuration.
    2. Empty the train, val, and test target folders to prevent accumulation from previous runs.
    3. Iterate through each emotion folder in the raw directory:
       - List all image file paths.
       - Shuffle the file list to ensure randomized distributions.
       - Calculate index splits (e.g., 70% train, 15% validation, 15% test).
       - Copy (or write) files to their destination split directories (maintaining subfolder class names).
    4. Log split counts for verification.
    
    Args:
        config (dict): Loaded application config.
        logger (logging.Logger): Centralized logging handle.
    """
    logger.info("Starting dataset splitting process...")
def load_config():
    data_dir=config['paths']['raw_data_dir']
    split_dir=config['paths']['split_data_dir']
    class_names=config['dataset']['classes']
    train_size=config['dataset']['split_ratio']['train']
    val_size=config['dataset']['split_ratio']['val']
    test_size=config['dataset']['split_ratio']['test']
    return data_dir,split_dir,class_names,train_size,val_size,test_size

def make_dir():
    data_dir,split_dir,class_names,train_size,val_size,test_size=load_config()
    if os.path.exists(split_dir):
        shutil.rmtree(split_dir)    
    for class_name in class_names:
        for s in ['train','val','test']:
            save_path=os.path.join(split_dir,s,class_name)
            os.makedirs(save_path,exist_ok=True)
    return 

def shuffle_files():
    class_names=load_config()
    for i in class_names:
        files=[os.listdir(f"data/raw/{i}")]
        random.shuffle(files)

def split_images():
    data_dir, split_dir, class_names, train_size, val_size, test_size = load_config()
    for class_name in class_names:
        class_path = os.path.join(data_dir, class_name)
        files = [file for file in os.listdir(class_path)]
        n=len(files)

        train_end=int(n*train_size)
        test=int(n*test_size)
        val_end=int(n*val_size)

        train_images = files[:train_end]
        val_images = files[train_end:val_end]
        test_images = files[val_end:]

        for filename in train_images:
            source = os.path.join(data_dir, class_name, filename)
            destination = os.path.join(
                split_dir, "train", class_name, filename
            )
            shutil.copy2(source, destination)

        for filename in val_images:
            source = os.path.join(data_dir, class_name, filename)
            destination = os.path.join(
                split_dir, "val", class_name, filename
            )
            shutil.copy2(source, destination)

        for filename in test_images:
            source = os.path.join(data_dir, class_name, filename)
            destination = os.path.join(
                split_dir, "test", class_name, filename
            )
            shutil.copy2(source, destination)


        # TODO: Implement file copying/moving, random shuffling, split boundary calculation.
    raise NotImplementedError("Implement split_dataset in src/dataset_prep.py")
