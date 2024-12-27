import sys
import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Use QTextEdit to display HTML. Let's style it:
        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        # Make background black, use a monospaced font, and white as default text color:
        self.ascii_display.setStyleSheet("""
            QTextEdit {
                background-color: black; 
                color: white; 
                font-family: 'Courier New', monospace; 
                font-size: 9pt;
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
        self.timer.start(30)  # ~33 fps

        # Extended ASCII character set (darkest -> brightest)
        # Source: https://stackoverflow.com/questions/47143332
        self.ascii_chars = list(" .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$")

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return  # No frame, do nothing

        # Debug (optional): print the shape to ensure it's non-zero
        # print("Frame shape:", frame.shape)

        # 1. (Skip brightness/contrast for now, to see raw color better)
        # frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=20)

        # 2. Resize to a bigger ASCII size for better detail
        width = 120
        height = 90
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # 3. Build HTML string with colored spans
        ascii_rows = []
        # Convert row to a bigger integer type to avoid overflow
        # We'll do it pixel by pixel below
        for row in resized_frame:
            row_html = ""
            for (b, g, r) in row.astype(np.uint16):
                # 4. Map (B,G,R) => intensity => ASCII char
                # Avoid overflow by using Python int
                intensity = (int(b) + int(g) + int(r)) // 3

                # Ensure index is in range
                char_index = int(intensity / 256 * len(self.ascii_chars))
                ascii_char = self.ascii_chars[max(0, min(char_index, len(self.ascii_chars) - 1))]

                # 5. Color the character using inline style
                row_html += f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'

            row_html += "<br>"
            ascii_rows.append(row_html)

        ascii_image_html = "".join(ascii_rows)

        # 6. Set the HTML in the QTextEdit
        self.ascii_display.setHtml(ascii_image_html)

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AsciiWebcam(camera_index=0)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
