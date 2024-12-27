import cv2

for backend in [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_MSMF]:
    print(f"Trying backend: {backend}")
    for i in range(5):  # Test indices 0..4
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            print(f"Camera index {i} is available on backend {backend}.")
            ret, frame = cap.read()
            if ret:
                print(f"Successfully read a frame from index {i} with backend {backend}.")
            cap.release()
        else:
            print(f"Camera index {i} is NOT available with backend {backend}.")
