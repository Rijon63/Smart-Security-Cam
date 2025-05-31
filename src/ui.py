import tkinter as tk
from tkinter import messagebox, Canvas, ttk, scrolledtext
import cv2
import threading
from PIL import Image, ImageTk
from src.utilities import correct_distortion
from src.video_processor import VideoProcessor
from config.config import OUTPUT_DIR, CAMERA_SOURCES, BOUNDARY_Y, BOUNDARY_COLOR, MIN_AREA, THRESHOLD
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UserInterface:
    def __init__(self, camera_manager):
        self.camera_manager = camera_manager
        self.root = tk.Tk()
        self.root.title("Smart Security Camera System")
        self.root.geometry("1000x700")
        self.running = True
        self.monitoring = False
        self.photo = None

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = Canvas(self.left_frame, width=700, height=500, bg='black')
        self.canvas.pack(pady=10)

        self.control_frame = ttk.Frame(self.left_frame)
        self.control_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(self.control_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(self.control_frame, text="Pause Monitoring", command=self.pause_monitoring, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.snapshot_button = ttk.Button(self.control_frame, text="Save Snapshot", command=self.save_snapshot, state=tk.DISABLED)
        self.snapshot_button.pack(side=tk.LEFT, padx=5)

        self.review_button = ttk.Button(self.control_frame, text="Review Recordings", command=self.review_recordings)
        self.review_button.pack(side=tk.LEFT, padx=5)

        self.quit_button = ttk.Button(self.control_frame, text="Quit", command=self.quit)
        self.quit_button.pack(side=tk.RIGHT, padx=5)

        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10)

        self.status_label = ttk.Label(self.right_frame, text="Camera Status", font=("Arial", 12, "bold"))
        self.status_label.pack(anchor=tk.NW)

        self.status_text = scrolledtext.ScrolledText(self.right_frame, width=30, height=10, state='disabled')
        self.status_text.pack(fill=tk.BOTH, pady=5)

        self.settings_frame = ttk.Frame(self.right_frame)
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.settings_frame, text="Boundary Y:").pack(side=tk.LEFT)
        self.boundary_y_var = tk.IntVar(value=BOUNDARY_Y)
        ttk.Entry(self.settings_frame, textvariable=self.boundary_y_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.settings_frame, text="Min Area:").pack(side=tk.LEFT)
        self.min_area_var = tk.IntVar(value=MIN_AREA)
        ttk.Entry(self.settings_frame, textvariable=self.min_area_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.settings_frame, text="Apply", command=self.apply_settings).pack(side=tk.LEFT)

        self.log_label = ttk.Label(self.right_frame, text="Motion Detection Log", font=("Arial", 12, "bold"))
        self.log_label.pack(anchor=tk.NW)

        self.log_text = scrolledtext.ScrolledText(self.right_frame, width=30, height=20, state='disabled')
        self.log_text.pack(fill=tk.BOTH, pady=5)

        self.update_camera_status()

    def update_camera_status(self):
        self.status_text.configure(state='normal')
        self.status_text.delete(1.0, tk.END)
        for i, source in enumerate(CAMERA_SOURCES):
            status = "Active" if self.camera_manager.processors[i].cap.isOpened() else "Inactive"
            self.status_text.insert(tk.END, f"Camera {i+1}: {status}\n")
        self.status_text.configure(state='disabled')

    def log_motion_event(self, event):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {event}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def start_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.start_button.configure(state=tk.DISABLED)
            self.pause_button.configure(state=tk.NORMAL)
            self.snapshot_button.configure(state=tk.NORMAL)
            threading.Thread(target=self.update_feed, daemon=True).start()

    def pause_monitoring(self):
        if self.monitoring:
            self.monitoring = False
            self.start_button.configure(text="Resume Monitoring", state=tk.NORMAL)
            self.pause_button.configure(state=tk.DISABLED)
            self.snapshot_button.configure(state=tk.DISABLED)
        else:
            self.monitoring = True
            self.start_button.configure(text="Start Monitoring", state=tk.DISABLED)
            self.pause_button.configure(state=tk.NORMAL)
            self.snapshot_button.configure(state=tk.NORMAL)
            threading.Thread(target=self.update_feed, daemon=True).start()

    def save_snapshot(self):
        frame, _, _, annotations = self.camera_manager.process_feeds()
        if frame is not None:
            # Draw annotations on snapshot
            for (x, y, w, h, label) in annotations:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = os.path.join(OUTPUT_DIR, f"snapshot_{timestamp}.jpg")
            cv2.imwrite(snapshot_path, frame)
            messagebox.showinfo("Snapshot Saved", f"Snapshot saved to {snapshot_path}")
        else:
            messagebox.showerror("Error", "Failed to capture snapshot")

    def review_recordings(self):
        try:
            videos = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(('.avi', '.mp4'))]
            if not videos:
                messagebox.showinfo("Info", "No recordings found.")
                return
            video_path = os.path.join(OUTPUT_DIR, videos[-1])
            logging.info(f"Playing video: {video_path}")
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                messagebox.showerror("Error", f"Failed to open video: {video_path}")
                return
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.imshow("Recording Playback", frame)
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            logging.error(f"Error in review_recordings: {e}")
            messagebox.showerror("Error", f"Failed to play recording: {e}")

    def apply_settings(self):
        global BOUNDARY_Y, MIN_AREA
        BOUNDARY_Y = self.boundary_y_var.get()
        MIN_AREA = self.min_area_var.get()
        logging.info(f"Updated BOUNDARY_Y to {BOUNDARY_Y}, MIN_AREA to {MIN_AREA}")
        # Reinitialize processors with updated config
        self.camera_manager.processors = [VideoProcessor(source) for source in CAMERA_SOURCES]

    def update_feed(self):
        def update():
            if not self.running or not self.monitoring:
                return
            try:
                frame, motion_detected, boundary_crossed, annotations = self.camera_manager.process_feeds()
                if frame is None:
                    logging.warning("No frame received from camera manager")
                    self.root.after(10, update)
                    return

                logging.debug(f"Frame received, shape: {frame.shape}")
                frame = correct_distortion(frame)

                # Draw annotations (green boxes and labels) on the live feed
                bottom_y = None
                for (x, y, w, h, label) in annotations:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    bottom_y = y + h  # Track the last object's bottom_y

                # Draw the boundary line on the frame
                cv2.line(frame, (0, BOUNDARY_Y), (frame.shape[1], BOUNDARY_Y), BOUNDARY_COLOR, 2)

                # Draw BOUNDARY_Y and bottom_y values for debugging
                cv2.putText(frame, f"BOUNDARY_Y: {BOUNDARY_Y}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                if bottom_y is not None:
                    cv2.putText(frame, f"Bottom Y: {bottom_y}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img = img.resize((700, 500), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

                if motion_detected:
                    self.log_motion_event("Motion detected!")
                if boundary_crossed:
                    self.log_motion_event("Boundary crossed! Recording started.")
                    messagebox.showinfo("Alert", "Boundary crossed! Recording started.")

            except Exception as e:
                logging.error(f"Error in update_feed: {e}")
            self.root.after(10, update)

        self.root.after(10, update)

    def quit(self):
        self.running = False
        self.monitoring = False
        self.camera_manager.release()
        self.root.quit()

    def run(self):
        self.root.mainloop()