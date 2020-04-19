import cv2
import numpy as np
import glob
import time
 
PATH="./garden_post_processing/"
out = None

for filename in sorted(glob.glob('{}*.jpg'.format(PATH))):
    img = cv2.imread(filename)
    font = cv2.FONT_HERSHEY_SIMPLEX
    try:
        height, width, layers = img.shape
        cv2.putText(img, filename, (0,height-10), font, .5,(255,255,255),2,cv2.LINE_AA)
        size = (width,height)
        if out is None:
            out = cv2.VideoWriter("{}.avi".format(time.time()), cv2.VideoWriter_fourcc(*'DIVX'), 15, size)
        out.write(img)
    except Exception as e:
        print("Trouble with image {}, e='{}'".format(filename, e))
 
out.release()