import cv2
import numpy as np
import json

class Camera():

    def __init__(self) -> None:
        self.range_filter = 'HSV'
        self.camera = cv2.VideoCapture(0)
        self.platform_coords = None
        self.image_ball_debug = None
        self.ball_in_area = False

       
    def set_track_ranges(self,TRACK_RANGES_FILE_PATH) -> None:

        with open(TRACK_RANGES_FILE_PATH,'rb')as fp:
            track_ranges = json.load(fp)
        ball_ranges = track_ranges['ball']

        self.track_ranges_min = (ball_ranges["H_min"],ball_ranges["S_min"],ball_ranges["V_min"])
        self.track_ranges_max = (ball_ranges["H_max"],ball_ranges["S_max"],ball_ranges["V_max"])

        if "rectangle_coords" in track_ranges.keys():
            self.platform_coords =  (
                track_ranges['rectangle_coords']["x"],
                track_ranges['rectangle_coords']["y"],
                track_ranges['rectangle_coords']["w"],
                track_ranges['rectangle_coords']["h"]
            )
        else:
            self.platform_coords = None
            self.blur =   track_ranges['platform']['blur']
            self.area_min =   track_ranges['platform']['area_min']
            self.threshold1 =   track_ranges['platform']['threshold1']
            self.threshold2 =   track_ranges['platform']['threshold2']
        
    
    def read_image(self)->None:
        ret, self.image = self.camera.read()
 
        if not ret:
            return None
        if self.platform_coords is not None:
            x,y,w,h = self.platform_coords
            self.image = self.image[y:y+h, x:x+w]

        if self.range_filter == 'RGB':
            self.frame_to_thresh = self.image.copy()
        else:
            self.frame_to_thresh = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)

    
    def get_ball_position(self):
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
        if radius> 20 and radius< 150:
            self.ball_in_area = True
            M = cv2.moments(c)
            self.ball_position = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
            
            self.setpoint = (
                int((self.platform_coords[2]/2)),
                int((self.platform_coords[3]/2))
            )
            
            self.error_x = self.ball_position[0]-self.setpoint[0]
            self.error_y = self.ball_position[1]-self.setpoint[1]

            absolute_error = np.linalg.norm(np.array(self.ball_position)-np.array(self.setpoint))

            self.image_ball_debug = self.image.copy()
            cv2.circle(self.image_ball_debug, (int(x), int(y)), int(radius),(0, 255, 255), 2)
            cv2.circle(self.image_ball_debug, self.ball_position , 3, (0, 0, 255), -1)
            cv2.circle(self.image_ball_debug, self.setpoint , 3, (0, 0, 255), -1)

            #draw error line
            cv2.line(self.image_ball_debug,self.setpoint,self.ball_position,(255, 0, 255),2)
            
            cv2.putText(self.image_ball_debug,"centroid", (self.ball_position [0]+10,self.ball_position [1]), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0, 0, 255),1)
            cv2.putText(self.image_ball_debug,"("+str(self.ball_position [0])+","+str(self.ball_position [1])+")", (self.ball_position [0]+10,self.ball_position [1]+15), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0, 0, 255),1)
        
            cv2.putText(self.image_ball_debug,"error: ", (self.setpoint [0]+10,self.setpoint [1]), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255, 0, 255),1)
            cv2.putText(self.image_ball_debug,str(int(absolute_error)), (self.setpoint [0]+10,self.setpoint [1]+15), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255, 0, 255),1)
        else:
            self.ball_in_area = False
        

    def find_platform(self)-> None:
        if self.platform_coords is None:
            self.read_image()
            self.__preprocess_platform()


            contours,_ = cv2.findContours(self.image_processed, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
            areas = [cv2.contourArea(cnt) for cnt in contours]

            index_maximum_area = np.argmax(areas)

            larger_contour = contours[index_maximum_area]

            area = cv2.contourArea(larger_contour) 
            if area > self.area_min:
                perimeter = cv2.arcLength(larger_contour,True)
                approx_geometry = cv2.approxPolyDP(larger_contour,0.02* perimeter,True)
                x_,y_,w,h = cv2.boundingRect(approx_geometry)
                self.platform_coords =  (x_,y_,w,h)
            else:
                self.platform_coords =  None

    
    def __preprocess_platform(self):
        image_blur = cv2.GaussianBlur(self.image,(9,9),self.blur)
        image_gray = cv2.cvtColor(image_blur,cv2.COLOR_BGR2GRAY)
        image_canny = cv2.Canny(image_gray,self.threshold1,self.threshold2)

        kernel = np.ones((5,5))
        self.image_processed = cv2.dilate(image_canny,kernel, iterations=1) 

        

    def calculate_ball_distance(self):
        if self.platform_coords is None:
            return None
    
    def show_camera_output(self):
        if self.ball_in_area:
            #cv2.imshow("result",cv2.rotate(self.image_ball_debug,cv2.ROTATE_90_CLOCKWISE))
            cv2.imshow("result",self.image_ball_debug)
        else:
            #cv2.imshow("result",cv2.rotate(self.image,cv2.ROTATE_90_CLOCKWISE))
            cv2.imshow("result",self.image)
        
        

 

            

    
    
    
        

        