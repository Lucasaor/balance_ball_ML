import cv2
import time

num =1
cap = cv2.VideoCapture(0)

try:
    while num < 4:
        ret, img  = cap.read()
        cv2.imshow('Frame', img)
        if cv2.waitKey(1) & 0xFF == ord('C'):
            cv2.imwrite('/home/pi/webcam_test/'+str(num)+'.jpg',img)
            print(f'Capture {num} sucessfull.')
            num += 1
finally:
    cap.release()
    cv2.destroyAllWindows()

