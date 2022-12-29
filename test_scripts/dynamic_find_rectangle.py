#reference: https://www.youtube.com/watch?v=Fchzk1lDt7Q

import cv2
import numpy as np

def empty(x):
    pass

def get_countours(image,image_contour):
    contours, hierarchy = cv2.findContours(image, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    for cnt in contours:
        area = cv2.contourArea(cnt) 
        area_min = cv2.getTrackbarPos("area_min","parameters")
        if area > area_min:
            cv2.drawContours(image_contour,cnt,-1,(255,0,255),7)
            perimeter = cv2.arcLength(cnt,True)
            approx_geometry = cv2.approxPolyDP(cnt,0.02* perimeter,True)
            x_,y_,w,h = cv2.boundingRect(approx_geometry)
            cv2.rectangle(image_contour,(x_,y_),(x_+w,y_+h),(0,255,0),5)

    



def main():
    camera = cv2.VideoCapture(0)

    cv2.namedWindow("parameters")
    cv2.resizeWindow("parameters",640,240)
    
    cv2.createTrackbar("blur","parameters",3,12,empty)
    cv2.createTrackbar("area_min","parameters",1500,5000,empty)
    cv2.createTrackbar("threshold1","parameters",120,255,empty)
    cv2.createTrackbar("threshold2","parameters",244,255,empty)

    # best features in test: (3,1500,120,244)

    while True:
        ret, image = camera.read()
        image_contour = image.copy()
        if not ret:
            break
        
        blur = cv2.getTrackbarPos("blur","parameters")

        image_blur = cv2.GaussianBlur(image,(9,9),blur)
        image_gray = cv2.cvtColor(image_blur,cv2.COLOR_BGR2GRAY)

        threshold1 = cv2.getTrackbarPos("threshold1","parameters")
        threshold2 = cv2.getTrackbarPos("threshold2","parameters")
        image_canny = cv2.Canny(image_gray,threshold1,threshold2)

        kernel = np.ones((5,5))
        image_dilate = cv2.dilate(image_canny,kernel, iterations=1) 

        get_countours(image_dilate,image_contour)

        cv2.imshow("result",image_contour)
        if cv2.waitKey(1) & 0xFF is ord('q'):
            break
            
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()