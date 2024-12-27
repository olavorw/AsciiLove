import sys
import cv2
import numpy as np
from PyQt5 import QtCore, QtWidgets

class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed (Forced 16:9)")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Display widget for ASCII output
        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        self.ascii_display.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: white;
                font-family: 'Cascadia Code', monospace;
                font-size: 14pt;
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(self.ascii_display)

        # Initialize camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open webcam (index {camera_index})")

        # Timer to grab frames
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(60)  # adjust as needed

        # Custom ASCII characters
        self.ascii_chars = list("█▓▒░ .'`^\",:;Il!i~+_-?][}{1▄█▌▀(|")

        # Saturation/brightness tweaks
        self.SATURATION_FACTOR = 1.5
        self.BRIGHTNESS_BOOST = 2.5

        # Final ASCII output dimensions (must be 16:9)
        # For example, 80 wide × 45 tall
        self.ascii_width  = 80
        self.ascii_height = 45  # 16:9 ratio => height = width * 9/16 => 80 * 9/16 = 45

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # 1. Convert to HSV to modify saturation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] *= self.SATURATION_FACTOR
        hsv[..., 2] *= self.BRIGHTNESS_BOOST
        hsv = np.clip(hsv, 0, 255).astype(np.uint8)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # 2. Crop the frame to 16:9
        cropped = self.crop_to_16_9(frame)

        # 3. Resize to final ASCII resolution (also 16:9)
        resized_frame = cv2.resize(
            cropped,
            (self.ascii_width, self.ascii_height),
            interpolation=cv2.INTER_AREA
        )

        # 4. Convert to ASCII
        ascii_rows = []
        for row in resized_frame:
            row_html = ""
            for (b, g, r) in row.astype(np.uint16):
                intensity = (int(b) + int(g) + int(r)) // 3
                char_index = int(intensity / 256 * len(self.ascii_chars))
                char_index = max(0, min(char_index, len(self.ascii_chars) - 1))
                ascii_char = self.ascii_chars[char_index]
                row_html += f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'
            row_html += "<br>"
            ascii_rows.append(row_html)

        ascii_image_html = "".join(ascii_rows)
        self.ascii_display.setHtml(ascii_image_html)

    def crop_to_16_9(self, frame):
        """
        Crops the input frame (H,W) to a 16:9 aspect ratio by center-cutting.
        """
        desired_ratio = 16 / 9
        h, w = frame.shape[:2]
        current_ratio = w / h

        if abs(current_ratio - desired_ratio) < 1e-5:
            # Already 16:9, no crop needed
            return frame

        if current_ratio > desired_ratio:
            # Too wide, crop width
            new_w = int(h * desired_ratio)
            offset = (w - new_w) // 2
            cropped = frame[:, offset:offset + new_w]
        else:
            # Too tall, crop height
            new_h = int(w / desired_ratio)
            offset = (h - new_h) // 2
            cropped = frame[offset:offset + new_h, :]

        return cropped

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    # Use the camera index that works on your machine (e.g., 0, 1, 3, etc.)
    window = AsciiWebcam(camera_index=3)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
