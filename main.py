import sys
import cv2
import numpy as np
import time
from PyQt5 import QtCore, QtGui, QtWidgets

# On Windows, forcing DirectShow can be faster than MSMF
BACKEND = cv2.CAP_DSHOW if sys.platform.startswith('win') else None

class AsciiData:
    """
    Simple container to hold a 2D array of (char, (r,g,b)) pairs
    representing the color ASCII 'frame'.
    """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # 2D list: ascii_pixels[y][x] = (char, (r,g,b))
        self.ascii_pixels = [[(" ", (255,255,255)) for _ in range(width)]
                             for _ in range(height)]


class AsciiWorker(QtCore.QObject):
    # Instead of sending a big string, we'll send an AsciiData object
    frame_ready = QtCore.pyqtSignal(AsciiData)
    finished    = QtCore.pyqtSignal()

    def __init__(self, camera_index=0, ascii_width=160, ascii_height=90):
        super().__init__()
        self.camera_index = camera_index
        self.ascii_width  = ascii_width
        self.ascii_height = ascii_height
        self._running     = True

        # **Color** ASCII palette (darkest -> brightest).
        # Feel free to expand or reorder for finer gradients.
        self.ascii_chars = list(" .:-=+*#%@")

        # HSV adjustments
        self.SATURATION_FACTOR = 2.5
        self.BRIGHTNESS_BOOST  = 2.0

        # Force 16:9
        self.desired_ratio = 16 / 9

    def start_capture(self):
        # Open camera (with optional backend)
        if BACKEND is not None:
            cap = cv2.VideoCapture(self.camera_index, BACKEND)
        else:
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"Failed to open camera index {self.camera_index}.")
            self.finished.emit()
            return

        # Try to set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 90)  # if your camera can do 90 FPS

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            # 1) HSV saturation/brightness
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[..., 1] *= self.SATURATION_FACTOR
            hsv[..., 2] *= self.BRIGHTNESS_BOOST
            hsv = np.clip(hsv, 0, 255).astype(np.uint8)
            frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # 2) Crop to 16:9
            frame_169 = self.crop_to_169(frame)

            # 3) Resize to ASCII grid size
            resized_frame = cv2.resize(
                frame_169,
                (self.ascii_width, self.ascii_height),
                interpolation=cv2.INTER_AREA
            )

            # 4) Convert to (char, (r,g,b)) 2D data
            ascii_data = self.frame_to_ascii_data(resized_frame)

            # 5) Emit to main thread
            self.frame_ready.emit(ascii_data)

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

    def frame_to_ascii_data(self, frame_bgr):
        """
        Build an AsciiData object with each pixel -> (char, (r,g,b)).
        """
        h, w = frame_bgr.shape[:2]
        out = AsciiData(width=w, height=h)

        # For each pixel, map intensity -> ascii char
        # Also store the original color (r,g,b).
        for y in range(h):
            row = frame_bgr[y]
            out_row = out.ascii_pixels[y]
            for x in range(w):
                b, g, r = row[x]
                intensity = (int(b) + int(g) + int(r)) // 3
                # pick char
                idx = int(intensity / 256 * len(self.ascii_chars))
                idx = max(0, min(idx, len(self.ascii_chars) - 1))
                ascii_char = self.ascii_chars[idx]
                out_row[x] = (ascii_char, (r, g, b))

        return out


class ColorAsciiWidget(QtWidgets.QWidget):
    """
    Custom widget to draw color ASCII using QPainter.
    Each 'pixel' is a single character with a specific pen color.
    """
    def __init__(self, ascii_width, ascii_height, parent=None):
        super().__init__(parent)
        self.ascii_width  = ascii_width
        self.ascii_height = ascii_height
        self.ascii_data   = None

        self.char_w = 9   # approximate width of each char
        self.char_h = 16  # approximate height of each char

        # We'll pick a monospaced font
        self.font = QtGui.QFont("Courier New", 14)
        self.setMinimumSize(self.ascii_width * self.char_w,
                            self.ascii_height * self.char_h)

    def update_ascii(self, ascii_data):
        """
        Receive an AsciiData object from the worker. Store and repaint.
        """
        self.ascii_data = ascii_data
        self.update()  # trigger paintEvent

    def paintEvent(self, event):
        if not self.ascii_data:
            return

        painter = QtGui.QPainter(self)
        painter.setFont(self.font)

        # For each pixel, set pen color, draw character
        for y in range(self.ascii_data.height):
            for x in range(self.ascii_data.width):
                char, (r, g, b) = self.ascii_data.ascii_pixels[y][x]
                painter.setPen(QtGui.QColor(r, g, b))

                # position on screen
                px = x * self.char_w
                py = (y+1) * self.char_h  # drawText baseline offset
                painter.drawText(px, py, char)


class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0, ascii_width=160, ascii_height=90):
        super().__init__()
        self.setWindowTitle("Color ASCII Webcam (High Res + Faster)")

        # Main widget
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Custom painting widget
        self.ascii_canvas = ColorAsciiWidget(ascii_width, ascii_height)
        layout.addWidget(self.ascii_canvas)

        # Worker + Thread
        self.worker_thread = QtCore.QThread()
        self.worker = AsciiWorker(
            camera_index=camera_index,
            ascii_width=ascii_width,
            ascii_height=ascii_height
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.start_capture)
        self.worker.frame_ready.connect(self.on_frame_ready)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker_thread.start()

    @QtCore.pyqtSlot(AsciiData)
    def on_frame_ready(self, ascii_data):
        # Update the painting widget with new data
        self.ascii_canvas.update_ascii(ascii_data)

    @QtCore.pyqtSlot()
    def on_worker_finished(self):
        self.worker_thread.quit()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker_thread.wait()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Try a big grid, e.g., 160×90 or 200×112.
    # The bigger you go, the heavier the rendering loop.
    window = AsciiWebcam(camera_index=3, ascii_width= 250, ascii_height=112)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
