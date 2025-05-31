import cv2
from datetime import datetime
from config.config import OUTPUT_DIR, COMPRESSED_DIR, FOURCC, FPS, BUFFER_SIZE
from src.utilities import compress_video
import logging
from collections import deque
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Recorder:
    def __init__(self):
        self.recording = False
        self.out = None
        self.timestamp = None
        self.buffer = deque(maxlen=BUFFER_SIZE)  # Buffer for 3 seconds of frames
        self.post_crossing_frames = 0  # Counter for frames after crossing
        self.frames_to_record_after = BUFFER_SIZE  # 3 seconds after crossing

    def add_to_buffer(self, frame, annotations):
        """Add a frame and its annotations to the buffer."""
        self.buffer.append((frame.copy(), annotations))

    def start_recording(self, frame):
        if not self.recording:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{OUTPUT_DIR}/crossing_{self.timestamp}.avi"
            self.out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*FOURCC), FPS, 
                                      (frame.shape[1], frame.shape[0]))
            self.recording = True
            logging.info(f"Started recording: {output_path}")

            # Write buffered frames (3 seconds before crossing)
            for buffered_frame, buffered_annotations in self.buffer:
                self.record_frame(buffered_frame, buffered_annotations)

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.out.release()
            self.out = None
            self.post_crossing_frames = 0
            input_path = f"{OUTPUT_DIR}/crossing_{self.timestamp}.avi"
            logging.info(f"Stopped recording: {input_path}")
            # Compress the video
            output_path = f"{COMPRESSED_DIR}/crossing_{self.timestamp}.mp4"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            compress_video(input_path, output_path)
            logging.info(f"Compressed video saved: {output_path}")

    def record_frame(self, frame, annotations):
        if self.recording:
            for (x, y, w, h, label) in annotations:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"Recording: {self.timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            self.out.write(frame)
            self.post_crossing_frames += 1
            if self.post_crossing_frames >= self.frames_to_record_after:
                self.stop_recording()