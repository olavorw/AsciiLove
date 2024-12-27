import sys
import cv2
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets

# On Windows, forcing DirectShow can be faster than MSMF
BACKEND = cv2.CAP_DSHOW if sys.platform.startswith('win') else None

class AsciiWorker(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(str)  # Plain text ASCII (no HTML)
    finished    = QtCore.pyqtSignal()

    def __init__(self, camera_index=0, ascii_width=80, ascii_height=45):
        super().__init__()
        self.camera_index = camera_index
        self.ascii_width  = ascii_width
        self.ascii_height = ascii_height
        self._running     = True

        # Monochrome ASCII palette
        self.ascii_chars = list("@%#*+=-:. ")

        # HSV adjustments (optional)
        self.SATURATION_FACTOR = 1.5
        self.BRIGHTNESS_BOOST  = 2.5

        # Force 16:9 cropping
        self.desired_ratio = 16 / 9

    def start_capture(self):
        """Loop capturing frames and converting them to ASCII until stopped."""
        if BACKEND is not None:
            cap = cv2.VideoCapture(self.camera_index, BACKEND)
        else:
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"Failed to open camera index {self.camera_index}.")
            self.finished.emit()
            return

        # Attempt to set camera properties if supported
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 90)  # If your camera truly does 90 FPS

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            # 1) Optional: HSV brightness/saturation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[..., 1] *= self.SATURATION_FACTOR
            hsv[..., 2] *= self.BRIGHTNESS_BOOST
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # 2) Crop to 16:9
            frame_169 = self.crop_to_169(frame)

            # 3) Resize to ASCII resolution
            resized_frame = cv2.resize(
                frame_169,
                (self.ascii_width, self.ascii_height),
                interpolation=cv2.INTER_AREA
            )

            # 4) Convert to plain-text ASCII (no HTML)
            ascii_text = self.frame_to_ascii(resized_frame)

            # 5) Emit the ASCII text
            self.frame_ready.emit(ascii_text)

        cap.release()
        self.finished.emit()

    def stop(self):
        self._running = False

    def crop_to_169(self, frame):
        """Center-crop the frame to a strict 16:9 aspect ratio."""
        h, w = frame.shape[:2]
        ratio = w / h
        if abs(ratio - self.desired_ratio) < 1e-5:
            return frame
        if ratio > self.desired_ratio:
            new_w = int(h * self.desired_ratio)
            offset = (w - new_w) // 2
            return frame[:, offset:offset + new_w]
        else:
            new_h = int(w / self.desired_ratio)
            offset = (h - new_h) // 2
            return frame[offset:offset + new_h, :]

    def frame_to_ascii(self, frame_bgr):
        """
        Convert a BGR frame to a multiline ASCII string.
        No color tags, just grayscale mapping => FAST.
        """
        rows = []
        for row in frame_bgr:
            row_chars = []
            for (b, g, r) in row.astype(np.uint16):
                intensity = (b + g + r) // 3
                char_index = int(intensity / 256 * len(self.ascii_chars))
                # clamp index
                char_index = max(0, min(char_index, len(self.ascii_chars) - 1))
                row_chars.append(self.ascii_chars[char_index])
            rows.append("".join(row_chars))

        # Join with newlines
        return "\n".join(rows)


class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0, ascii_width=80, ascii_height=45):
        super().__init__()

        self.setWindowTitle("Monochrome ASCII Webcam (High FPS)")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # QPlainTextEdit for fast plain-text display
        self.ascii_display = QtWidgets.QPlainTextEdit()
        self.ascii_display.setReadOnly(True)
        self.ascii_display.setStyleSheet("""
            QPlainTextEdit {
                background-color: black;
                color: white;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.ascii_display)

        # Create worker + thread
        self.worker_thread = QtCore.QThread()
        self.worker = AsciiWorker(
            camera_index=camera_index,
            ascii_width=ascii_width,
            ascii_height=ascii_height
        )
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.start_capture)
        self.worker.frame_ready.connect(self.on_frame_ready)
        self.worker.finished.connect(self.on_worker_finished)

        self.worker_thread.start()

    @QtCore.pyqtSlot(str)
    def on_frame_ready(self, ascii_text):
        # Update the QPlainTextEdit with plain text
        self.ascii_display.setPlainText(ascii_text)

    @QtCore.pyqtSlot()
    def on_worker_finished(self):
        self.worker_thread.quit()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker_thread.wait()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    # For a bigger ASCII grid, you could try 160×90, but 80×45 is a good start for high FPS
    window = AsciiWebcam(camera_index=3, ascii_width=80, ascii_height=45)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
