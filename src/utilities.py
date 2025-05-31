import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def compress_video(input_path, output_path):
    """Compress a video file using H.264."""
    cap = cv2.VideoCapture(input_path)
    fourcc = cv2.VideoWriter_fourcc(*"H264")
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
    
    cap.release()
    out.release()

def correct_distortion(frame):
    h, w = frame.shape[:2]
    K = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]])  # Camera matrix
    D = np.array([0.1, -0.2, 0, 0])  # Distortion coefficients (adjust these)
    map1, map2 = cv2.initUndistortRectifyMap(K, D, None, K, (w, h), cv2.CV_16SC2)
    return cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR)

def stitch_images(images):
    """Stitch multiple images into a single frame."""
    if len(images) == 0:
        return None
    if len(images) == 1:
        return images[0]
    stitcher = cv2.Stitcher_create()
    status, stitched = stitcher.stitch(images)
    if status == cv2.Stitcher_OK:
        return stitched
    else:
        logging.warning(f"Stitching failed with status {status}. Falling back to side-by-side layout.")
        max_height = max(img.shape[0] for img in images)
        resized_images = [cv2.resize(img, (int(img.shape[1] * max_height / img.shape[0]), max_height)) for img in images]
        return np.hstack(resized_images)