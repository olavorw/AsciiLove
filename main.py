import sys
from io import BytesIO

import requests
from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QSlider, \
    QLineEdit, QTextEdit
import qdarkstyle

ASCII_CHARS = "@$B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/|()1{}[]?-_+~<>i!lI;:,\"^`'. "


def resize_image(image, new_width=100):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(aspect_ratio * new_width * 0.55)
    resized_image = image.resize((new_width, new_height))
    return resized_image


def grayify(image):
    """
    Convert the image to grayscale
    :param image:
    :return: Grayscale image
    """
    return image.convert("L")


def pixels_to_ascii(image):
    """
    Convert the pixels to ASCII characters
    :param image:
    :return: ASCII string
    """
    pixels = image.getdata()
    ascii_str = ""
    for pixel_value in pixels:
        ascii_str += ASCII_CHARS[pixel_value // 25]
    return ascii_str


def download_image_from_url(url):
    """
    Download image from URL
    :param url:
    :return: Image object
    """
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content))
    else:
        print("Failed to download image")
        return None


def convert_image_to_ascii(image_path: object, new_width: object = 100) -> object:
    """
    Convert the image to ASCII art
    :param image_path:
    :param new_width:
    :return: ASCII art string
    """
    try:
        if image_path.startswith("http"):
            image = download_image_from_url(image_path)
        else:
            image = Image.open(image_path)
    except Exception as e:
        print(f"Unable to open image file {image_path}.")
        return ""

    image = resize_image(image, new_width)
    image = grayify(image)

    ascii_str = pixels_to_ascii(image)
    img_width = image.width

    # Format the string into rows to match image height
    ascii_art = "\n".join([ascii_str[i:i + img_width] for i in range(0, len(ascii_str), img_width)])

    return ascii_art


class ASCIIArtApp(QMainWindow):
    def __init__(self):
        """
        Initialize the main window
        """
        super().__init__()
        self.setWindowTitle("ASCII Art Generator")
        self.setGeometry(100, 100, 1100, 1100)

        self.layout = QVBoxLayout()

        self.image_path_input = QLineEdit(self)
        self.image_path_input.setPlaceholderText("Enter image file path or URL here...")
        self.layout.addWidget(self.image_path_input)

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_image)
        self.layout.addWidget(self.browse_button)

        self.width_slider = QSlider(Qt.Horizontal, self)
        self.width_slider.setMinimum(20)
        self.width_slider.setMaximum(200)
        self.width_slider.setValue(100)
        self.layout.addWidget(self.width_slider)

        self.generate_button = QPushButton("Generate ASCII Art", self)
        self.generate_button.clicked.connect(self.generate_ascii_art)
        self.layout.addWidget(self.generate_button)

        self.ascii_art_display = QTextEdit(self)
        self.ascii_art_display.setReadOnly(True)
        self.ascii_art_display.setFontFamily("Courier")
        self.ascii_art_display.setFontPointSize(8)
        self.layout.addWidget(self.ascii_art_display)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def browse_image(self):
        """
        Open file dialog to browse image file
        """
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "",
                                                   "Images (*.png *.xpm *.jpg *.jpeg *.bmp);;All Files (*)",
                                                   options=options)
        if file_name:
            self.image_path_input.setText(file_name)

    def generate_ascii_art(self):
        """
        Generate ASCII art from the image
        :rtype: object
        """
        image_path = self.image_path_input.text()
        new_width = self.width_slider.value()
        ascii_art = convert_image_to_ascii(image_path, new_width)
        if ascii_art:
            self.ascii_art_display.setText(ascii_art)
        else:
            self.ascii_art_display.setText("Failed to generate ASCII art. Please check the image path or URL.")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    window = ASCIIArtApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
