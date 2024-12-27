import sys
import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

class AsciiWebcam(QtWidgets.QMainWindow):
    def __init__(self, camera_index=0):
        super().__init__()

        self.setWindowTitle("Live Color ASCII Webcam Feed")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        self.ascii_display = QtWidgets.QTextEdit()
        self.ascii_display.setReadOnly(True)
        layout.addWidget(self.ascii_display)

        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open webcam (index {camera_index})")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Extended ASCII character set
        self.ascii_chars = list(" .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$")

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # 1. OPTIONAL: Adjust brightness or do gamma correction
        alpha = 1.2  # contrast
        beta = 20    # brightness
        frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        # 2. Resize to a manageable ASCII size
        width = 80
        height = 60
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # 3. Build HTML string
        ascii_rows = []
        for row in resized_frame:
            row_html = ""
            # Convert row to a larger integer type to avoid overflow
            row_16 = row.astype(np.uint16)

            for (b_16, g_16, r_16) in row_16:
                # 4. SAFE addition to avoid overflow
                intensity = (int(b_16) + int(g_16) + int(r_16)) // 3

                char_index = int(intensity / 256 * len(self.ascii_chars))
                ascii_char = self.ascii_chars[char_index]

                # 5. Color the character
                row_html += f'<span style="color: rgb({r_16},{g_16},{b_16});">{ascii_char}</span>'

            row_html += "<br>"
            ascii_rows.append(row_html)

        ascii_image_html = "".join(ascii_rows)
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
