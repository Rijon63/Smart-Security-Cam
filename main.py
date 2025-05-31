from src.camera_manager import CameraManager
from src.ui import UserInterface
from config.config import CAMERA_SOURCES, OUTPUT_DIR, COMPRESSED_DIR
import os

if __name__ == "__main__":
    # Ensure output directories exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(COMPRESSED_DIR):
        os.makedirs(COMPRESSED_DIR)

    # Initialize system
    camera_manager = CameraManager(CAMERA_SOURCES)
    ui = UserInterface(camera_manager)
    ui.run()