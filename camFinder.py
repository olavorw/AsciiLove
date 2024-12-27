import cv2

for i in range(100):  # Try 0 through 4 (or more if you have many cameras)
    try:
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Camera index {i} is available.")
            cap.release()
    except Exception as e:
        continue
