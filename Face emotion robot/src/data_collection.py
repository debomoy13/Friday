import os
import cv2
import time
from src.utils import load_face_cascade

"""from src.utils import load_face_cascade"""

def collect_data(config, logger):
    # TARGET EMOTION CLASS - Change this manually for other classes (e.g., "sad", "angry", etc.)
    emotion_class = "happy"
 
    logger.info(f"Initializing webcam data collection for: {emotion_class}")
    
    # 1. Setup save directory
    raw_dir = config.get("paths", {}).get("raw_data_dir", "data/raw")
    target_dir = os.path.join(raw_dir, emotion_class)
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        face_config = config["webcam"]["face_detection"]
        cascade_path = face_config["cascade_path"]
        scale_factor = face_config["scale_factor"]
        min_neighbors = face_config["min_neighbors"]
        
        face_cascade = load_face_cascade(cascade_path)
    except Exception as e:
        logger.error(f"Failed to load face detector: {e}")
        return

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        logger.error("Failed to open webcam")
        return

    saved_count = 0
    max_images = 100
    last_save_time = 0.0
    save_interval = 1

    logger.info("Data collection started. Face the camera. Press 'q' to quit.")

    while saved_count < max_images:
        ret, frame = cam.read()
        if not ret:
            logger.warning("Could not read frame from webcam.")
            break

        # Convert to grayscale for Haar Cascades detector
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=(30, 30)
        )

        current_time = time.time()
        saved_this_frame = False

        # Highlight detected faces and crop the primary face
        for idx, (x, y, w, h) in enumerate(faces):
            # Draw green rectangle for the primary face, blue for additional faces
            color = (0, 255, 0) if idx == 0 else (255, 0, 0)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            # Crop and save only the primary face at specific time interval
            if idx == 0 and (current_time - last_save_time >= save_interval):
                # Ensure the crop is within frame boundaries
                y_start, y_end = max(0, y), min(frame.shape[0], y+h)
                x_start, x_end = max(0, x), min(frame.shape[1], x+w)
                face_crop = frame[y_start:y_end, x_start:x_end]

                # Save face crop to target folder
                timestamp = int(time.time() * 1000)
                img_name = f"face_{timestamp}.jpg"
                img_path = os.path.join(target_dir, img_name)
                cv2.imwrite(img_path, face_crop)

                saved_count += 1
                last_save_time = current_time
                saved_this_frame = True
                logger.info(f"[{saved_count}/{max_images}] Saved face crop to: {img_path}")

        # Render HUD Overlay
        # Background bar for readability
        cv2.rectangle(frame, (0, 0), (200, 100), (0, 0, 0), -1)
        
        cv2.putText(frame, f"Emotion Class: {emotion_class.upper()}", (10, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        cv2.putText(frame, f"Progress: {saved_count} / {max_images}", (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
        
        status_text = "Capturing..." if len(faces) > 0 else "Searching for face..."
        status_color = (0, 255, 0) if len(faces) > 0 else (0, 0, 255)
        cv2.putText(frame, f"Status: {status_text}", (10, 75), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1, cv2.LINE_AA)

        cv2.putText(frame, "Press 'q' to quit", (10, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # Show webcam window
        cv2.imshow("Face Emotion Robot - Data Collection", frame)

        # Listen for quit key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logger.info("Data collection loop terminated early by user.")
            break

    cam.release()
    cv2.destroyAllWindows()
    logger.info(f"Finished. Captured {saved_count} new images.")
