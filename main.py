#!/usr/bin/env python3
"""
Real-time ASCII webcam viewer with PyQt5.
Entire script. Single-file solution.

Make sure you have:
  pip install opencv-python pyqt5 pillow numpy

Change the FONT_PATH to point to a valid TTF font on your system.
"""

import sys
import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap


def measure_char_dimensions(char, font, stroke_width=0):
    """
    Returns (width, height) for a single character `char` using Pillow's textbbox().

    textbbox() returns (left, top, right, bottom), so (width, height) = (right-left, bottom-top).
    """
    temp_img = Image.new("RGB", (1, 1), "black")
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
    left, top, right, bottom = bbox
    return (right - left, bottom - top)


def get_font_bitmaps(fontsize, boldness, reverse, background, chars, font_path):
    """
    Returns a list of font bitmaps (numpy arrays) for the given ASCII characters,
    sorted by pixel density for the mapping from dark->light (or reversed).

    1. We measure each character's bounding box using measure_char_dimensions().
    2. We keep track of the min width & min height across all chars.
    3. We render each char to an RGB image, then crop to (min_width, min_height).
    4. If background=255 (white), invert so the char "foreground" is white in the numeric array.
    5. Sort by pixel sum to produce an ordered ramp (darkest -> lightest or reversed).
    """
    bitmaps = {}
    min_width = min_height = float('inf')
    font_ttf = ImageFont.truetype(font_path, size=fontsize)

    # Measure first
    for char in chars:
        if char in bitmaps:
            continue
        w, h = measure_char_dimensions(char, font_ttf, stroke_width=boldness)
        min_width = min(min_width, w)
        min_height = min(min_height, h)
        bitmaps[char] = (w, h)

    # Render with consistent bounding
    rendered_bitmaps = {}
    for char in chars:
        (w, h) = bitmaps[char]
        # Make an image that fits the measured w, h
        img = Image.new('RGB', (w, h), (background,)*3)
        draw = ImageDraw.Draw(img)
        draw.text(
            (0, 0),
            char,
            fill=(255 - background,)*3,
            font=font_ttf,
            stroke_width=boldness
        )
        bitmap = np.array(img, dtype=np.uint8)

        # If background=255 => invert so 'char' is white in the numeric array.
        if background == 255:
            np.subtract(255, bitmap, out=bitmap)

        # Crop to the (min_width, min_height) if needed
        rendered_bitmaps[char] = bitmap[: int(min_height), : int(min_width)]

    # Sort the bitmaps by pixel density
    sorted_chars = sorted(
        rendered_bitmaps.keys(),
        key=lambda c: rendered_bitmaps[c].sum(),
        reverse=not reverse
    )
    # Return as an array in sorted order
    fonts = [rendered_bitmaps[c] for c in sorted_chars]
    return np.array(fonts)


def draw_ascii(frame, chars, background, clip, monochrome, font_bitmaps, buffer=None):
    """
    Convert an RGB image (H x W x 3) to an ASCII representation using font_bitmaps.

    Steps:
      1) Downsample the frame to 1 pixel per ASCII "cell".
      2) Map each pixel's luminosity -> index in font_bitmaps (which is sorted by density).
      3) Composite that character's bitmap onto a buffer scaled back up.
    """
    if len(font_bitmaps) == 0:
        # No font bitmaps means no ASCII
        return frame

    # fh -> font height, fw -> font width
    fh, fw = font_bitmaps[0].shape[:2]
    oh, ow = frame.shape[:2]  # original frame size

    # Step 1: Downsample
    frame_small = frame[::fh, ::fw]  # shape: (h, w, 3)
    h, w = frame_small.shape[:2]

    # Step 2: Create a buffer for compositing the final ASCII image
    if buffer is None:
        dtype = np.uint16 if len(chars) < 32 else np.uint32
        buffer = np.empty((h * fh, w * fw, 3), dtype=dtype)

    buffer_view = buffer[:h*fh, :w*fw]

    # Step 2a: If using a monochrome color
    if len(monochrome) != 0:
        buffer_view[:] = 1
        # If background=255, invert the user-chosen color
        color = 255 - monochrome if background == 255 else monochrome
        np.multiply(buffer_view, color, out=buffer_view)
    else:
        # Use original frame's color (inverted if background=255)
        if background == 255:
            frame_small = 255 - frame_small
        # Expand each pixel back up to (fh x fw)
        for row_small in range(h):
            for col_small in range(w):
                buffer_view[
                row_small*fh:(row_small+1)*fh,
                col_small*fw:(col_small+1)*fw
                ] = frame_small[row_small, col_small]

    # Step 3: Compute luminosity => index
    # Weighted sum: R*3 + G*4 + B*1 => approximate brightness
    gray_index = np.sum(frame_small * [3, 4, 1], axis=2)  # shape: (h, w)

    # scale -> 0..(len(chars)-1)
    # max sum: (3+4+1)*255=2040 => ~ /2048 => >> 11
    gray_index = gray_index * len(chars)
    gray_index >>= 11

    # Step 4: Retrieve the corresponding font bitmap
    # font_bitmaps shape: (len(chars), fh, fw, 3)
    # Selecting with [gray_index] => shape (h, w, fh, fw, 3)
    # Then we transpose to combine (h, fh) and (w, fw)
    ascii_image = font_bitmaps[gray_index].transpose(0, 2, 1, 3, 4).reshape(h*fh, w*fw, 3)

    # Step 5: Clip to original size if needed
    if clip:
        ascii_image = ascii_image[:oh, :ow]
        buffer_view = buffer_view[:oh, :ow]
        buffer = buffer[:oh, :ow]

    # Step 6: Multiply ASCII char (ascii_image) by color (buffer_view), scale down by 255
    np.multiply(ascii_image, buffer_view, out=buffer)
    np.floor_divide(buffer, 255, out=buffer)

    # Convert to uint8
    buffer = buffer.astype(np.uint8, copy=False)
    # If background=255 => invert final
    if background == 255:
        np.subtract(255, buffer, out=buffer)

    return buffer


class ASCIICamera(QWidget):
    def __init__(self):
        super().__init__()

        # --- Basic GUI setup
        self.setWindowTitle("Real-Time ASCII Webcam (PyQt5)")
        self.layout = QVBoxLayout()
        self.label = QLabel("Initializing camera...")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        # --- ASCII conversion parameters
        self.chars = np.array(list("@%#*+=-:. "))  # default ASCII set
        self.reverse = False
        self.fontsize = 16   # smaller helps see more detail
        self.boldness = 2
        self.background = 0  # black background by default
        self.clip = True
        self.monochrome = np.array([], dtype=np.uint16)  # empty => use color from frame

        # For your font path, pick a TTF that definitely exists
        # Windows example: "C:/Windows/Fonts/Arial.ttf"
        # Linux example: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        # Mac example: "/Library/Fonts/Arial.ttf"
        self.FONT_PATH = "C:/Windows/Fonts/Arial.ttf"

        # --- Precompute font bitmaps
        try:
            self.font_bitmaps = get_font_bitmaps(
                self.fontsize,
                self.boldness,
                self.reverse,
                self.background,
                self.chars,
                self.FONT_PATH
            )
        except Exception as e:
            print("Error creating font bitmaps:", e)
            self.font_bitmaps = []

        # --- OpenCV camera init
        self.cap = cv2.VideoCapture(0)  # 0 => default camera
        if not self.cap.isOpened():
            self.label.setText("ERROR: Could not open webcam.")
            return

        # --- QTimer to periodically grab frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        # ~30 ms => ~33 FPS
        self.timer.start(30)

        self.buffer = None  # optional buffer reuse

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.label.setText("ERROR: No frame from camera.")
            return

        # Convert from BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # For debugging, if you suspect ASCII conversion is failing:
        #   self.show_raw(frame_rgb)
        #   return

        # ASCII conversion
        ascii_frame = draw_ascii(
            frame_rgb,
            self.chars,
            self.background,
            self.clip,
            self.monochrome,
            self.font_bitmaps,
            self.buffer
        )
        # Save buffer for next iteration
        self.buffer = ascii_frame

        # Convert ascii_frame (numpy) -> QImage -> QPixmap -> show in label
        h, w, ch = ascii_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(ascii_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(q_img))

    def show_raw(self, frame_rgb):
        """
        Debug helper: show the raw camera feed as a normal color image
        in the same label, bypassing ASCII.
        """
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(q_img))

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = ASCIICamera()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
