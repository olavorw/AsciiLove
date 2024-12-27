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
        # Make background black, use a monospaced font, larger font size, and add letter spacing.
        # 'letter-spacing: 2px;' ensures more space between characters horizontally.
        self.ascii_display.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: white;
                font-family: 'Cascadia Code', monospace;
                font-size: 14pt;
                letter-spacing: 2px; /* Increase if you want even more spacing */
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
        self.timer.start(60)  # ~66 fps

        # Fewer ASCII characters (darkest -> brightest), for a bolder look
        # Example: " .:-=+*#@"
        self.ascii_chars = list("█▓▒░ .'`^\",:;Il!i~+_-?][}{1▄█▌▀(|")

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return  # No frame, do nothing

        # 1. Resize to a manageable ASCII size
        width = 80
        height = 60
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # 2. Build HTML string with colored spans
        ascii_rows = []
        for row in resized_frame:
            row_html = ""
            for (b, g, r) in row.astype(np.uint16):
                # Convert (b, g, r) to intensity
                intensity = (int(b) + int(g) + int(r)) // 3

                # Map intensity to ASCII char
                char_index = int(intensity / 256 * len(self.ascii_chars))
                # Ensure index is in range
                char_index = max(0, min(char_index, len(self.ascii_chars) - 1))
                ascii_char = self.ascii_chars[char_index]

                # Color the character
                row_html += f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'

            row_html += "<br>"
            ascii_rows.append(row_html)

        ascii_image_html = "".join(ascii_rows)

        # 3. Set the HTML in the QTextEdit
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
