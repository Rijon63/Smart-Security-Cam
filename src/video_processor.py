import cv2
import numpy as np
import imutils
import torch
from config.config import MIN_AREA, THRESHOLD, FRAME_WIDTH, BOUNDARY_Y
import logging
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoProcessor:
    def __init__(self, source):
        logging.info(f"Initializing VideoProcessor with source: {source}")
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            logging.error(f"Failed to open video source: {source}")
            raise ValueError(f"Failed to open video source: {source}")
        self.fgbg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        try:
            self.tracker = cv2.TrackerCSRT_create()
        except AttributeError:
            logging.error("OpenCV tracking module not available. Install opencv-contrib-python.")
            raise AttributeError("OpenCV tracking module not available. Install opencv-contrib-python.")
        self.tracking = False
        self.bbox = None
        self.recent_y = deque(maxlen=5)  # Store last 5 bottom_y values
        self.last_y = None  # Store the previous bottom_y for consecutive frame comparison

    def process_frame(self, frame):
        logging.debug("Processing frame")
        frame = imutils.resize(frame, width=FRAME_WIDTH)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        fgmask = self.fgbg.apply(gray)
        thresh = cv2.threshold(fgmask, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False
        boundary_crossed = False
        annotations = []

        # YOLOv5 object detection
        results = self.model(frame)
        for *xyxy, conf, cls in results.xyxy[0]:
            if conf > 0.5:
                x, y, w, h = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]-xyxy[0]), int(xyxy[3]-xyxy[1])
                label = self.model.names[int(cls)].capitalize()
                if label in ["Person", "Car", "Truck"]:
                    motion_detected = True
                    annotations.append((x, y, w, h, label))
                    bottom_y = y + h
                    logging.debug(f"Detected {label} at bottom_y={bottom_y}, BOUNDARY_Y={BOUNDARY_Y}")

                    # Update recent_y and check for crossing
                    self.recent_y.append(bottom_y)
                    if self.last_y is not None:
                        if (self.last_y < BOUNDARY_Y and bottom_y >= BOUNDARY_Y) or \
                           (self.last_y > BOUNDARY_Y and bottom_y <= BOUNDARY_Y):
                            boundary_crossed = True
                            logging.info(f"Boundary crossed by detected object! last_y={self.last_y}, bottom_y={bottom_y}")
                    self.last_y = bottom_y

                    # Reinitialize tracker if not tracking or tracking failed
                    if not self.tracking:
                        self.bbox = (x, y, w, h)
                        self.tracker.init(frame, self.bbox)
                        self.tracking = True

        if self.tracking:
            success, self.bbox = self.tracker.update(frame)
            if success:
                (x, y, w, h) = [int(v) for v in self.bbox]
                annotations.append((x, y, w, h, "Tracked Object"))
                bottom_y = y + h
                logging.debug(f"Tracked object at bottom_y={bottom_y}, BOUNDARY_Y={BOUNDARY_Y}")

                # Update recent_y and check for crossing
                self.recent_y.append(bottom_y)
                if self.last_y is not None:
                    if (self.last_y < BOUNDARY_Y and bottom_y >= BOUNDARY_Y) or \
                       (self.last_y > BOUNDARY_Y and bottom_y <= BOUNDARY_Y):
                        boundary_crossed = True
                        logging.info(f"Boundary crossed by tracked object! last_y={self.last_y}, bottom_y={bottom_y}")
                self.last_y = bottom_y
            else:
                self.tracking = False
                self.last_y = None
                logging.debug("Tracker lost object, awaiting new detection")

        # Log recent_y for debugging
        if self.recent_y:
            logging.debug(f"Recent Y values: {list(self.recent_y)}")

        return frame, motion_detected, boundary_crossed, annotations

    def release(self):
        self.cap.release()