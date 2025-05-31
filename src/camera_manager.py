from src.video_processor import VideoProcessor
from src.recorder import Recorder
from src.utilities import stitch_images
import cv2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CameraManager:
    def __init__(self, sources):
        logging.info("Initializing CameraManager")
        self.processors = [VideoProcessor(source) for source in sources]
        self.recorders = [Recorder() for _ in sources]

    def process_feeds(self):
        frames = []
        motion_detected = False
        boundary_crossed = False
        all_annotations = []

        for i, processor in enumerate(self.processors):
            ret, frame = processor.cap.read()
            if not ret:
                logging.warning(f"Failed to read frame from camera {i}")
                continue

            logging.debug(f"Frame read from camera {i}, shape: {frame.shape}")
            frame, detected, crossed, annotations = processor.process_frame(frame)
            frames.append(frame)
            all_annotations.append(annotations)

            # Always add the frame to the buffer
            self.recorders[i].add_to_buffer(frame, annotations)

            if detected:
                motion_detected = True
                logging.info(f"Motion detected by camera {i}")

            if crossed:
                boundary_crossed = True
                self.recorders[i].start_recording(frame)
            elif self.recorders[i].recording:
                self.recorders[i].record_frame(frame, annotations)

        if len(frames) > 1:
            logging.info("Stitching frames")
            stitched_frame = stitch_images(frames)
            # Combine annotations for stitched frame (simplified: use first camera's annotations)
            stitched_annotations = all_annotations[0] if all_annotations else []
        else:
            stitched_frame = frames[0] if frames else None
            stitched_annotations = all_annotations[0] if all_annotations else []

        if stitched_frame is not None:
            logging.debug(f"Returning stitched frame, shape: {stitched_frame.shape}")
        else:
            logging.warning("No frames to return")
        return stitched_frame, motion_detected, boundary_crossed, stitched_annotations

    def release(self):
        for processor in self.processors:
            processor.release()
        for recorder in self.recorders:
            recorder.stop_recording()