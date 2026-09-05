import argparse
import sys
from src.config import load_config
from src.logger import setup_logger

def main():
    parser = argparse.ArgumentParser(
        description="Real-Time Facial Expression Recognition System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py collect              # Collect images via webcam
  python main.py split                # Split raw dataset into Train/Val/Test
  python main.py train                # Train the custom CNN model
  python main.py evaluate             # Evaluate the model on test split
  python main.py predict --mode webcam # Run real-time webcam inference
  python main.py predict --mode image --path my_face.jpg  # Predict single image
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # Subcommand: collect
    subparsers.add_parser("collect", help="Run interactive webcam tool to capture and crop face images")
    
    # Subcommand: split
    subparsers.add_parser("split", help="Process and split raw data folder into train/val/test datasets")
    
    # Subcommand: train
    subparsers.add_parser("train", help="Run model training and validation pipeline")
    
    # Subcommand: evaluate
    subparsers.add_parser("evaluate", help="Run test set evaluation (confusion matrix, precision/recall)")
    
    # Subcommand: predict
    predict_parser = subparsers.add_parser("predict", help="Execute model inference (image or live webcam)")
    predict_parser.add_argument(
        "--mode", 
        choices=["webcam", "image"], 
        default="webcam", 
        help="Prediction mode: 'webcam' (real-time stream) or 'image' (static file)"
    )
    predict_parser.add_argument(
        "--path", 
        type=str, 
        default=None, 
        help="Path to input image file (required if --mode is 'image')"
    )

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    # Load configuration settings
    try:
        config = load_config()
        output_dir = config.get("paths", {}).get("output_dir", "outputs")
        logger = setup_logger(output_dir)
    except Exception as e:
        print(f"FATAL: Failed to initialize application: {e}")
        sys.exit(1)
        
    logger.info(f"Running command: {args.command}")
    
    try:
        if args.command == "collect":
            from src.data_collection import collect_data
            collect_data(config, logger)
            
        elif args.command == "split":
            from src.dataset_prep import split_dataset
            split_dataset(config, logger)
            
        elif args.command == "train":
            from src.train import train_model
            train_model(config, logger)
            
        elif args.command == "evaluate":
            from src.evaluate import evaluate_model
            evaluate_model(config, logger)
            
        elif args.command == "predict":
            from src.predict import predict_image, predict_webcam
            if args.mode == "image":
                if not args.path:
                    logger.error("Error: --path is required when --mode is 'image'")
                    sys.exit(1)
                predict_image(args.path, config, logger)
            else:
                predict_webcam(config, logger)
                
    except NotImplementedError as nie:
        logger.error(f"Feature not yet implemented: {nie}")
        logger.info("Please implement the corresponding function in the designated source file.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Execution cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
