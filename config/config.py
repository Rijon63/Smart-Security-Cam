import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "security_clips")
COMPRESSED_DIR = os.path.join(BASE_DIR, "output", "compressed_clips")

CAMERA_SOURCES = [0]
FRAME_WIDTH = 500

MIN_AREA = 100
THRESHOLD = 20

FPS = 20.0
FOURCC = "XVID"

# Boundary settings (for a horizontal line)
BOUNDARY_Y = 360  # Default to middle of 720p frame (720/2)
BOUNDARY_COLOR = (255, 0, 0)  # Blue color for the boundary line

# Buffer settings
BUFFER_SECONDS = 3  # Seconds to buffer before and after crossing
BUFFER_SIZE = int(FPS * BUFFER_SECONDS)  # Number of frames to buffer (e.g., 20 FPS * 3 seconds = 60 frames)