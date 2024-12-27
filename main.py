import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and set layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Use QTextEdit (instead of QPlainTextEdit) so we can display HTML with color
        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        layout.addWidget(self.ascii_display)

        # Initialize the webcam
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open webcam (index {camera_index})")

        # Create a timer to periodically fetch and convert frames
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 fps

        # A more extensive ASCII character set (darkest -> brightest).
        # Reference / inspiration:
        # https://stackoverflow.com/questions/47143332/converting-an-image-to-ascii-image-in-python
        # https://paulbourke.net/dataformats/asciiart/
        self.ascii_chars = list(" .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$")

    def update_frame(self):
        """Read frame from webcam, convert to color ASCII, and update display."""
        ret, frame = self.cap.read()
        if not ret:
            return

        # 1. Resize for ASCII display (smaller = faster + more readable)
        width = 80  # Adjust as needed for your screen
        height = 60
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # 2. Convert each pixel to an ASCII character + color
        # We'll build an HTML string with <span style="color:rgb(...)">char</span>
        ascii_rows = []
        for row in resized_frame:
            row_html = ""
            for (b, g, r) in row:
                # Calculate intensity to pick which ASCII character to use
                intensity = (b + g + r) // 3
                char_index = int(intensity / 256 * len(self.ascii_chars))
                ascii_char = self.ascii_chars[char_index]

                # Generate a colored HTML span for this character
                row_html += f'<span style="color: rgb({r},{g},{b});">{ascii_char}</span>'
            # End of row, add a line break
            row_html += "<br>"
            ascii_rows.append(row_html)

        # 3. Join everything into a single HTML string
        ascii_image_html = "".join(ascii_rows)

        # 4. Display the colored ASCII art in our QTextEdit
        self.ascii_display.setHtml(ascii_image_html)

    def closeEvent(self, event):
        """Release the camera when the window is closed."""
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
