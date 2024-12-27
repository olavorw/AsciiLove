import sys
import cv2
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets

# Uncomment on Windows to force DirectShow (faster than MSMF for many setups)
# BACKEND = cv2.CAP_DSHOW
# On other OS, you might leave it as None or use another backend
BACKEND = cv2.CAP_DSHOW if sys.platform.startswith('win') else None

class AsciiWorker(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(str)  # Emitted with the HTML string
    finished    = QtCore.pyqtSignal()

    def __init__(self, camera_index=0, ascii_width=160, ascii_height=90):
        super().__init__()
        self.camera_index  = camera_index
        self.ascii_width   = ascii_width
        self.ascii_height  = ascii_height
        self._running      = True

        # ASCII character set
        self.ascii_chars = list("#$2 .'`^\",:;Il!i~+_-?][/10#OoW(|")

        # HSV adjustments
        self.SATURATION_FACTOR = 1.5
        self.BRIGHTNESS_BOOST  = 2.5

        # Force 16:9
        self.desired_ratio = 16 / 9

    def start_capture(self):
        # Try opening the camera with an optional backend
        if BACKEND is not None:
            cap = cv2.VideoCapture(self.camera_index, BACKEND)
        else:
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"Failed to open camera index {self.camera_index}.")
            self.finished.emit()
            return

        # Attempt to set camera properties if supported
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # or your preferred resolution
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 60)  # attempt 60 FPS if camera allows

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            # 1) Boost saturation/brightness in HSV
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

            # 4) Convert to ASCII HTML
            ascii_html = self.frame_to_ascii(resized_frame)

            # 5) Emit result
            self.frame_ready.emit(ascii_html)

            # No sleep! Burn those CPU cycles for max FPS

        cap.release()
        self.finished.emit()

    def stop(self):
        self._running = False

    def crop_to_169(self, frame):
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
        Convert a BGR frame to an HTML string with colored ASCII spans.
        Optimized by building strings in a single pass.
        """
        rows_html = []
        append_row_html = rows_html.append

        for row in frame_bgr:
            row_spans = []
            append_span = row_spans.append

            for (b, g, r) in row.astype(np.uint16):
                intensity = (b + g + r) // 3
                char_index = int(intensity / 256 * len(self.ascii_chars))
                char_index = max(0, min(char_index, len(self.ascii_chars) - 1))
                ascii_char = self.ascii_chars[char_index]
                append_span(
                    f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'
                )

            # Join spans in one pass
            append_row_html("".join(row_spans))

        # Join rows with <br>
        return "<br>".join(rows_html)


class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0, ascii_width=160, ascii_height=90):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed (Max FPS Attempt)")
        self.setGeometry(100, 100, 1280, 720)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        self.ascii_display.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: white;
                font-family: 'Cascadia Code', monospace;
                font-size: 10pt;
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(self.ascii_display)

        # Worker + Thread
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

        # Start thread
        self.worker_thread.start()

        # Optional: raise thread priority
        self.set_high_priority()

    @QtCore.pyqtSlot(str)
    def on_frame_ready(self, ascii_html):
        self.ascii_display.setHtml(ascii_html)

    @QtCore.pyqtSlot()
    def on_worker_finished(self):
        self.worker_thread.quit()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker_thread.wait()
        super().closeEvent(event)

    def set_high_priority(self):
        """
        Attempt to raise the thread priority.
        Not guaranteed to work on all platforms,
        but might help in some Windows environments.
        """
        # On Windows/PyQt, we can do:
        self.worker_thread.setPriority(QtCore.QThread.TimeCriticalPriority)
        # Alternatively, QThread.HighestPriority or QThread.InheritPriority


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Go big! 320 wide × 180 tall = more detail + 16:9
    # Might be CPU heavy, but let's see if we can push it
    window = AsciiWebcam(camera_index=0, ascii_width=100, ascii_height=50)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
