import cv2
import numpy as np
import json

class Camera():

    def __init__(self) -> None:
        self.range_filter = 'HSV'
        self.camera = cv2.VideoCapture(0)

       
    def set_track_ranges(self,TRACK_RANGES_FILE_PATH) -> None:

        with open(TRACK_RANGES_FILE_PATH,'rb')as fp:
            track_ranges = json.load(fp)
        self.track_ranges_min = (track_ranges["H_min"],track_ranges["S_min"],track_ranges["V_min"])
        self.track_ranges_max = (track_ranges["H_max"],track_ranges["S_max"],track_ranges["V_max"])
    
    
    def read_image(self)->None:
        ret, self.image = self.camera.read()
 
        if not ret:
            return None

        if self.range_filter == 'RGB':
            self.frame_to_thresh = self.image.copy()
        else:
            self.frame_to_thresh = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)
    
    def get_circle_center(self)-> tuple:
        self.read_image()
        # filter the selected color
        thresh = cv2.inRange(self.frame_to_thresh,self.track_ranges_min,self.track_ranges_max)

        #build mask
        kernel = np.ones((5,5),np.uint8)
        mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None
 
        # only proceed if at least one contour was found
        if len(cnts) < 1:
            return None
        
        # find the largest contour in the mask, then use
        # it to compute the minimum enclosing circle and
        # centroid
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        return (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

    def find_platform(self)-> None:
        self.read_image()
        

    
    
    
        

        