import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

class HighResWebcamFeed(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()
        self.setWindowTitle("High-Resolution Webcam Feed")
        self.setGeometry(100, 100, 1280, 720)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create a label to display the webcam feed
        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.video_label)

        # Initialize the camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open webcam (index {camera_index})")

        # Attempt to set high resolution and frame rate
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Create a timer to periodically update frames
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~30 fps

    def update_frame(self):
        """Captures a frame from the webcam and updates the label."""
        ret, frame = self.cap.read()
        if ret:
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to QImage
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_img = QtGui.QImage(frame.data, width, height, bytes_per_line,
                                 QtGui.QImage.Format_RGB888)

            # Convert QImage to QPixmap (no scaling)
            pixmap = QtGui.QPixmap.fromImage(q_img)
            self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        """Release the camera resource when closing the window."""
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = HighResWebcamFeed(camera_index=0)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
