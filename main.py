import sys
import cv2
import numpy as np
from PyQt5 import QtCore, QtWidgets

class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed (More Saturation!)")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Use QTextEdit to display HTML. Let's style it:
        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        # Make background black, use a monospaced font, larger font size, and letter spacing
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
        self.timer.start(60)  # ~16 FPS (60 ms intervals) or tune to your preference

        # Custom ASCII character set with block/braille-like characters
        self.ascii_chars = list("█▓▒░ .'`^\",:;Il!i~+_-?][}{1▄█▌▀(|")

        # Tweak these factors to increase saturation/brightness
        self.SATURATION_FACTOR = 1.5   # Increase for more vibrant colors
        self.BRIGHTNESS_BOOST  = 1.0   # Increase for more brightness (1.0 = no change)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return  # No frame, do nothing

        # --------------------------------------------
        # 1. Convert to HSV to modify saturation
        # --------------------------------------------
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)

        # hsv[..., 0] is the Hue channel
        # hsv[..., 1] is the Saturation channel
        # hsv[..., 2] is the Value (brightness) channel

        # Multiply Saturation by a factor
        hsv[..., 1] *= self.SATURATION_FACTOR
        # Multiply Value for brightness boost, if desired
        hsv[..., 2] *= self.BRIGHTNESS_BOOST

        # Clip values to valid HSV range [0,255]
        hsv = np.clip(hsv, 0, 255).astype(np.uint8)

        # Convert HSV back to BGR for ASCII mapping
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # --------------------------------------------
        # 2. Resize for ASCII
        # --------------------------------------------
        width = 80
        height = 60
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # --------------------------------------------
        # 3. Convert to ASCII + color
        # --------------------------------------------
        ascii_rows = []
        for row in resized_frame:
            row_html = ""
            for (b, g, r) in row.astype(np.uint16):
                intensity = (int(b) + int(g) + int(r)) // 3
                char_index = int(intensity / 256 * len(self.ascii_chars))
                char_index = max(0, min(char_index, len(self.ascii_chars) - 1))
                ascii_char = self.ascii_chars[char_index]

                # Build HTML for this character with inline color
                row_html += f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'

            row_html += "<br>"
            ascii_rows.append(row_html)

        ascii_image_html = "".join(ascii_rows)

        # --------------------------------------------
        # 4. Render the ASCII art in the QTextEdit
        # --------------------------------------------
        self.ascii_display.setHtml(ascii_image_html)

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AsciiWebcam(camera_index=3)  # or 0, 1, etc. depending on your system
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
