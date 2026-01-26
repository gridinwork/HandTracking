import sys

import cv2
import numpy as np
import mediapipe as mp

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
    QVBoxLayout,
)


def list_available_cameras(max_devices=5):
    available = []
    for index in range(max_devices):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue
        ret, frame = cap.read()
        if ret and frame is not None:
            available.append(index)
        cap.release()
    if not available:
        available = [0]
    return available


class CameraManager:
    def __init__(self, index=0):
        self.cap = None
        self.index = None
        self.set_camera(index)

    def set_camera(self, index):
        if self.index == index and self.cap is not None:
            return
        if self.cap is not None:
            self.cap.release()
        self.index = index
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class HolisticTracker:
    def __init__(self):
        # Holistic provides pose (shoulder/elbow/wrist) + hands.
        self.holistic = mp.solutions.holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            refine_face_landmarks=False,
        )

    def process(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(frame_rgb)
        return results


class SkeletonDrawer:
    def __init__(self):
        self.hand_connections = list(mp.solutions.hands.HAND_CONNECTIONS)
        self.pose_connections = [
            # Left arm
            (mp.solutions.pose.PoseLandmark.LEFT_SHOULDER, mp.solutions.pose.PoseLandmark.LEFT_ELBOW),
            (mp.solutions.pose.PoseLandmark.LEFT_ELBOW, mp.solutions.pose.PoseLandmark.LEFT_WRIST),
            # Right arm
            (mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER, mp.solutions.pose.PoseLandmark.RIGHT_ELBOW),
            (mp.solutions.pose.PoseLandmark.RIGHT_ELBOW, mp.solutions.pose.PoseLandmark.RIGHT_WRIST),
        ]
        self.joint_color = (0, 200, 255)
        self.bone_color = (0, 255, 0)
        self.arm_color = (255, 128, 0)
        self.palm_color = (0, 0, 255)
        self.background_color = (20, 20, 20)

    def draw(self, frame_shape, results):
        height, width = frame_shape[:2]
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        canvas[:] = self.background_color

        if results is None:
            return canvas

        # Draw arms from pose landmarks (shoulder -> elbow -> wrist).
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            for start_id, end_id in self.pose_connections:
                start = landmarks[start_id]
                end = landmarks[end_id]
                x1, y1 = int(start.x * width), int(start.y * height)
                x2, y2 = int(end.x * width), int(end.y * height)
                cv2.line(canvas, (x1, y1), (x2, y2), self.arm_color, 5)
                cv2.circle(canvas, (x1, y1), 7, self.arm_color, -1)
                cv2.circle(canvas, (x2, y2), 7, self.arm_color, -1)

        # Draw left hand skeleton if detected.
        if results.left_hand_landmarks:
            self.draw_hand(canvas, results.left_hand_landmarks, width, height)

        # Draw right hand skeleton if detected.
        if results.right_hand_landmarks:
            self.draw_hand(canvas, results.right_hand_landmarks, width, height)

        return canvas

    def draw_hand(self, canvas, hand_landmarks, width, height):
        landmarks = hand_landmarks.landmark

        # Palm quad: index_mcp -> middle_mcp -> ring_mcp -> pinky_mcp.
        palm_indices = [5, 9, 13, 17]
        palm_points = [
            (int(landmarks[i].x * width), int(landmarks[i].y * height))
            for i in palm_indices
        ]
        for i in range(len(palm_points)):
            start = palm_points[i]
            end = palm_points[(i + 1) % len(palm_points)]
            cv2.line(canvas, start, end, self.palm_color, 5)

        # Connect wrist to center of the palm quad.
        wrist = landmarks[0]
        wrist_pt = (int(wrist.x * width), int(wrist.y * height))
        palm_center = (
            int(sum(p[0] for p in palm_points) / len(palm_points)),
            int(sum(p[1] for p in palm_points) / len(palm_points)),
        )
        cv2.line(canvas, wrist_pt, palm_center, self.palm_color, 5)
        cv2.circle(canvas, wrist_pt, 7, self.palm_color, -1)
        cv2.circle(canvas, palm_center, 7, self.palm_color, -1)

        # Draw finger bones from MediaPipe connections.
        for connection in self.hand_connections:
            start = landmarks[connection[0]]
            end = landmarks[connection[1]]
            x1, y1 = int(start.x * width), int(start.y * height)
            x2, y2 = int(end.x * width), int(end.y * height)
            cv2.line(canvas, (x1, y1), (x2, y2), self.bone_color, 4)

        for lm in landmarks:
            x, y = int(lm.x * width), int(lm.y * height)
            cv2.circle(canvas, (x, y), 6, self.joint_color, -1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandTracking_Version_3")

        self.camera_manager = CameraManager(index=0)
        self.holistic_tracker = HolisticTracker()
        self.skeleton_drawer = SkeletonDrawer()

        self.left_label = QLabel()
        self.right_label = QLabel()
        self.left_label.setAlignment(Qt.AlignCenter)
        self.right_label.setAlignment(Qt.AlignCenter)
        self.left_label.setMinimumSize(480, 360)
        self.right_label.setMinimumSize(480, 360)

        self.camera_combo = QComboBox()
        self.available_cameras = list_available_cameras(max_devices=8)
        for index in self.available_cameras:
            self.camera_combo.addItem(f"Camera {index}", index)
        self.camera_combo.setCurrentIndex(0)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)

        self.start_stop_button = QPushButton("Stop")
        self.start_stop_button.clicked.connect(self.toggle_stream)
        self.is_streaming = True

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Camera:"))
        controls_layout.addWidget(self.camera_combo)
        controls_layout.addWidget(self.start_stop_button)
        controls_layout.addStretch()

        video_layout = QHBoxLayout()
        video_layout.addWidget(self.left_label)
        video_layout.addWidget(self.right_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(video_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)

    def on_camera_changed(self, index):
        camera_index = self.camera_combo.itemData(index)
        if camera_index is not None:
            self.camera_manager.set_camera(camera_index)

    def toggle_stream(self):
        if self.is_streaming:
            self.timer.stop()
            self.camera_manager.release()
            self.start_stop_button.setText("Start")
            self.is_streaming = False
            self.show_placeholders()
        else:
            camera_index = self.camera_combo.currentData()
            if camera_index is None:
                camera_index = 0
            self.camera_manager.set_camera(camera_index)
            self.timer.start(30)
            self.start_stop_button.setText("Stop")
            self.is_streaming = True

    def update_frames(self):
        ret, frame = self.camera_manager.read()
        if not ret or frame is None:
            self.show_placeholders()
            return

        self.set_label_image(self.left_label, frame)

        results = self.holistic_tracker.process(frame)
        skeleton = self.skeleton_drawer.draw(frame.shape, results)
        self.set_label_image(self.right_label, skeleton)

    def show_placeholders(self):
        placeholder = np.zeros((360, 480, 3), dtype=np.uint8)
        placeholder[:] = (20, 20, 20)
        self.set_label_image(self.left_label, placeholder)
        self.set_label_image(self.right_label, placeholder)

    def set_label_image(self, label, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        height, width = frame_rgb.shape[:2]
        bytes_per_line = width * 3
        q_image = QImage(
            frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_image)
        label.setPixmap(
            pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def closeEvent(self, event):
        self.timer.stop()
        self.camera_manager.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1200, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
